import json
import mimetypes
import math
import os
import io
import zipfile
from xml.sax.saxutils import escape
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import Body, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from .database import Base, SessionLocal, apply_sqlite_compat_migrations, engine
from .models import AnalysisJob
from .tasks import process_analysis

app = FastAPI(
    title="AudioSplit & Cifra Pro API",
    version="0.3.0",
    description="API de orquestração para separação de fontes e análise musical.",
)
# Fail closed: production must explicitly provide the exact frontend origins.
origins = [item.strip() for item in os.getenv("CORS_ORIGINS", "").split(",") if item.strip() and item.strip() != "*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["*"],
)

MAX_UPLOAD_BYTES = 250 * 1024 * 1024
ALLOWED_SUFFIXES = {".mp3", ".wav", ".flac", ".m4a", ".ogg"}
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/data/uploads"))
Base.metadata.create_all(bind=engine)
apply_sqlite_compat_migrations()


class JobStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class JobAccepted(BaseModel):
    job_id: str
    status: JobStatus
    created_at: datetime
    message: str


class JobDetails(JobAccepted):
    progress: int = 0
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    result_available: bool = False


class TimedEvent(BaseModel):
    start: float = Field(ge=0, description="Tempo inicial em segundos")
    end: float = Field(gt=0, description="Tempo final em segundos")
    label: str
    confidence: Optional[float] = Field(default=None, ge=0, le=1)
    source: Optional[str] = None


class ChordEvent(TimedEvent):
    label: str = Field(description="Símbolo do acorde, por exemplo Dm7 ou G7(b9)")


class LyricToken(TimedEvent):
    label: str = Field(description="Palavra ou sílaba reconhecida")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "audiosplit-cifra-pro",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/v1/jobs", response_model=JobAccepted, status_code=202)
async def create_analysis_job(audio: UploadFile = File(...)):
    # Normalize client-supplied names before storing them or returning them in headers.
    raw_name = (audio.filename or "audio").replace("\\", "/")
    original_name = Path(raw_name).name
    original_name = "".join(
        character for character in original_name
        if ord(character) >= 32 and ord(character) != 127
    ).strip()[:180] or "audio"
    suffix = Path(original_name).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=415, detail="Formato não suportado.")
    job_id = str(uuid4())
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    destination = UPLOAD_DIR / f"{job_id}{suffix}"
    total = 0
    try:
        with destination.open("wb") as output:
            while chunk := await audio.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="Arquivo excede o limite de 250 MB.")
                output.write(chunk)
        if total == 0:
            raise HTTPException(status_code=400, detail="Arquivo vazio.")

        created_at = datetime.now(timezone.utc)
        with SessionLocal() as db:
            db.add(AnalysisJob(
                id=job_id,
                status=JobStatus.queued.value,
                original_filename=original_name,
                audio_path=str(destination),
                created_at=created_at,
                updated_at=created_at,
                progress=0,
                message="Arquivo recebido; aguardando worker.",
            ))
            db.commit()
        process_analysis.delay(job_id)
        return JobAccepted(
            job_id=job_id,
            status=JobStatus.queued,
            created_at=created_at,
            message="Áudio recebido e enviado para processamento.",
        )
    except HTTPException:
        destination.unlink(missing_ok=True)
        raise
    except Exception as exc:
        destination.unlink(missing_ok=True)
        with SessionLocal() as db:
            db.query(AnalysisJob).filter(AnalysisJob.id == job_id).delete()
            db.commit()
        raise HTTPException(status_code=503, detail="Não foi possível registrar o processamento.") from exc
    finally:
        await audio.close()


@app.get("/v1/jobs/{job_id}", response_model=JobDetails)
async def get_job(job_id: str):
    with SessionLocal() as db:
        job = db.get(AnalysisJob, job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Processamento não encontrado.")
        return JobDetails(
            job_id=job.id,
            status=JobStatus(job.status),
            created_at=job.created_at,
            message=job.message or "Estado atual do processamento.",
            progress=job.progress or 0,
            error_code=job.error_code,
            error_message=job.error_message,
            result_available=bool(job.result_json),
        )


@app.get("/v1/jobs/{job_id}/result")
async def get_job_result(job_id: str):
    with SessionLocal() as db:
        job = db.get(AnalysisJob, job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Processamento não encontrado.")
        if job.status != JobStatus.completed.value or not job.result_json:
            raise HTTPException(status_code=409, detail="Resultado ainda não está disponível.")
        return json.loads(job.result_json)


@app.put("/v1/jobs/{job_id}/result")
async def update_job_result(job_id: str, payload: dict = Body(...)):
    if payload.get("job_id") != job_id:
        raise HTTPException(status_code=400, detail="O identificador do projeto não corresponde ao job.")
    transcription = payload.get("transcription") or {}
    if not isinstance(transcription, dict):
        raise HTTPException(status_code=422, detail="Objeto de transcrição inválido.")
    words = transcription.get("words", [])
    chords = payload.get("chords", [])
    if not isinstance(words, list) or not isinstance(chords, list):
        raise HTTPException(status_code=422, detail="Lista de eventos inválida.")
    for event in words + chords:
        try:
            start, end = float(event["start"]), float(event["end"])
        except (KeyError, TypeError, ValueError):
            raise HTTPException(status_code=422, detail="Evento sem timestamps válidos.")
        if not math.isfinite(start) or not math.isfinite(end) or start < 0 or end <= start or not str(event.get("label", "")).strip():
            raise HTTPException(status_code=422, detail="Evento com intervalo ou rótulo inválido.")
    with SessionLocal() as db:
        job = db.get(AnalysisJob, job_id)
        if job is None or job.status != JobStatus.completed.value:
            raise HTTPException(status_code=404, detail="Projeto concluído não encontrado.")
        job.result_json = json.dumps(payload, ensure_ascii=False)
        job.updated_at = datetime.now(timezone.utc)
        job.message = "Revisões manuais salvas."
        db.commit()
    result_path = Path(os.getenv("DATA_DIR", "/data")) / "jobs" / job_id / "result.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return {"saved": True, "job_id": job_id, "message": "Revisões salvas no projeto."}


@app.get("/v1/jobs/{job_id}/source")
async def download_source(job_id: str):
    with SessionLocal() as db:
        job = db.get(AnalysisJob, job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Projeto não encontrado.")
        source_path = Path(job.audio_path)
        if not source_path.is_file():
            raise HTTPException(status_code=404, detail="Áudio original não encontrado.")
        media_type = mimetypes.guess_type(source_path.name)[0] or "application/octet-stream"
        return FileResponse(source_path, media_type=media_type, filename=Path(job.original_filename).name)


def _create_analysis_pdf(payload: dict) -> bytes:
    """Builds a real UTF-8-capable PDF with lyric timing and chord events."""
    buffer = io.BytesIO()
    regular_font = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    bold_font = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
    if regular_font.is_file() and bold_font.is_file():
        if "AudioSplitDejaVu" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont("AudioSplitDejaVu", str(regular_font)))
            pdfmetrics.registerFont(TTFont("AudioSplitDejaVu-Bold", str(bold_font)))
        font_name, bold_name = "AudioSplitDejaVu", "AudioSplitDejaVu-Bold"
    else:
        font_name, bold_name = "Helvetica", "Helvetica-Bold"

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ASBody", parent=styles["BodyText"], fontName=font_name, fontSize=9, leading=13))
    styles.add(ParagraphStyle(name="ASTitle", parent=styles["Title"], fontName=bold_name, fontSize=18, leading=22, alignment=TA_CENTER))
    styles.add(ParagraphStyle(name="ASHeading", parent=styles["Heading2"], fontName=bold_name, fontSize=12, leading=16, spaceBefore=10, spaceAfter=6))
    styles.add(ParagraphStyle(name="ASChord", parent=styles["BodyText"], fontName=bold_name, textColor=colors.HexColor("#9A741A"), fontSize=9, leading=12))
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=16*mm, leftMargin=16*mm, topMargin=15*mm, bottomMargin=15*mm)
    story = []
    audio = payload.get("audio") or {}
    transcription = payload.get("transcription") or {}
    words = transcription.get("words") or []
    chords = payload.get("chords") or []
    title = escape(Path(str(audio.get("source_filename") or "Análise musical")).stem)
    story.extend([Paragraph(title, styles["ASTitle"]), Spacer(1, 5*mm)])
    meta = []
    if payload.get("job_id"):
        meta.append("Projeto: " + escape(str(payload["job_id"])))
    if audio.get("duration_seconds") is not None:
        meta.append("Duração: " + str(audio["duration_seconds"]) + " s")
    tempo = (payload.get("rhythm") or {}).get("tempo_bpm")
    if tempo:
        meta.append("BPM estimado: " + str(tempo))
    story.append(Paragraph(" · ".join(meta) if meta else "AudioSplit & Cifra Pro", styles["ASBody"]))
    story.append(Paragraph("Letra com cifras e tempos", styles["ASHeading"]))
    if words:
        assigned = {}
        for chord in chords:
            index = next((i for i, word in enumerate(words) if float(word.get("end", 0)) >= float(chord.get("start", 0))), None)
            if index is not None:
                assigned.setdefault(index, []).append(str(chord.get("label", "")))
        lyric_data = [[Paragraph("<b>Tempo</b>", styles["ASBody"]), Paragraph("<b>Cifra</b>", styles["ASBody"]), Paragraph("<b>Palavra / sílaba</b>", styles["ASBody"])]]
        for index, word in enumerate(words):
            chord_text = " · ".join(assigned.get(index, []))
            lyric_data.append([
                Paragraph(f'{float(word.get("start", 0)):.2f}s', styles["ASBody"]),
                Paragraph(escape(chord_text), styles["ASChord"]),
                Paragraph(escape(str(word.get("label", ""))), styles["ASBody"]),
            ])
        lyric_table = Table(lyric_data, colWidths=[22*mm, 30*mm, 120*mm], repeatRows=1)
        lyric_table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#EDE7D7")),
            ("GRID", (0,0), (-1,-1), 0.25, colors.HexColor("#D2D2D2")),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("LEFTPADDING", (0,0), (-1,-1), 5), ("RIGHTPADDING", (0,0), (-1,-1), 5),
            ("TOPPADDING", (0,0), (-1,-1), 4), ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        story.append(lyric_table)
    else:
        edited = escape(str(transcription.get("edited_text") or "Nenhuma palavra reconhecida."))
        story.append(Paragraph(edited, styles["ASBody"]))
    story.append(Paragraph("Eventos harmônicos", styles["ASHeading"]))
    chord_data = [[Paragraph("<b>Início</b>", styles["ASBody"]), Paragraph("<b>Fim</b>", styles["ASBody"]), Paragraph("<b>Acorde</b>", styles["ASBody"]), Paragraph("<b>Confiança</b>", styles["ASBody"])]]
    for chord in chords:
        confidence = chord.get("confidence")
        chord_data.append([
            Paragraph(f'{float(chord.get("start", 0)):.2f}s', styles["ASBody"]),
            Paragraph(f'{float(chord.get("end", 0)):.2f}s', styles["ASBody"]),
            Paragraph(escape(str(chord.get("label", ""))), styles["ASChord"]),
            Paragraph("—" if confidence is None else f'{float(confidence)*100:.0f}%', styles["ASBody"]),
        ])
    if len(chord_data) == 1:
        chord_data.append([Paragraph("Nenhum acorde reconhecido", styles["ASBody"]), "", "", ""])
    chord_table = Table(chord_data, colWidths=[25*mm, 25*mm, 75*mm, 35*mm], repeatRows=1)
    chord_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#EDE7D7")),
        ("GRID", (0,0), (-1,-1), 0.25, colors.HexColor("#D2D2D2")),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("SPAN", (0,1), (-1,1)) if len(chord_data) == 2 and not chords else ("LEFTPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING", (0,0), (-1,-1), 5), ("RIGHTPADDING", (0,0), (-1,-1), 5),
        ("TOPPADDING", (0,0), (-1,-1), 4), ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(chord_table)
    story.append(Spacer(1, 6*mm))
    story.append(Paragraph("Observação: letra, alinhamento e acordes são resultados automáticos. Em músicas cantadas, revise especialmente sílabas, antecipações, contratempos, inversões e mudanças harmônicas rápidas.", styles["ASBody"]))
    doc.build(story)
    return buffer.getvalue()


@app.get("/v1/jobs/{job_id}/export.pdf")
async def export_analysis_pdf(job_id: str):
    with SessionLocal() as db:
        job = db.get(AnalysisJob, job_id)
        if job is None or job.status != JobStatus.completed.value or not job.result_json:
            raise HTTPException(status_code=404, detail="Análise concluída não encontrada.")
        payload = json.loads(job.result_json)
    pdf_bytes = _create_analysis_pdf(payload)
    filename = f"audiosplit-cifras-{job_id}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@app.get("/v1/jobs/{job_id}/stems.zip")
async def download_all_stems(job_id: str):
    """Gera ZIP com todos os stems WAV existentes para uma análise concluída."""
    with SessionLocal() as db:
        job = db.get(AnalysisJob, job_id)
        if job is None or job.status != JobStatus.completed.value:
            raise HTTPException(status_code=404, detail="Análise concluída não encontrada.")
        job_dir = Path(os.getenv("DATA_DIR", "/data")) / "jobs" / job_id
        names = ("vocals", "drums", "bass", "guitar", "piano", "other")
        available = [name for name in names if (job_dir / f"{name}.wav").is_file()]
        if not available:
            raise HTTPException(status_code=404, detail="Nenhuma faixa separada foi encontrada.")
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            for name in available:
                bundle.write(job_dir / f"{name}.wav", arcname=f"{name}.wav")
        archive.seek(0)
        return StreamingResponse(
            archive,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="audiosplit-stems-{job_id}.zip"'}
        )


@app.get("/v1/jobs/{job_id}/stems/{stem_name}")
async def download_stem(job_id: str, stem_name: str):
    if stem_name not in {"vocals", "drums", "bass", "guitar", "piano", "other"}:
        raise HTTPException(status_code=404, detail="Stem não encontrado.")
    with SessionLocal() as db:
        job = db.get(AnalysisJob, job_id)
        if job is None or job.status != JobStatus.completed.value:
            raise HTTPException(status_code=404, detail="Arquivo não encontrado.")
        data_dir = Path(os.getenv("DATA_DIR", "/data"))
        stem_path = data_dir / "jobs" / job_id / f"{stem_name}.wav"
        if not stem_path.is_file():
            raise HTTPException(status_code=404, detail="Arquivo de áudio não encontrado.")
        return FileResponse(stem_path, media_type="audio/wav", filename=f"{stem_name}.wav")
