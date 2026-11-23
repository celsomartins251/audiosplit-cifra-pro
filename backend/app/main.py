import os
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from .database import Base, SessionLocal, engine
from .models import AnalysisJob
from .tasks import process_analysis

app = FastAPI(
    title="AudioSplit & Cifra Pro API",
    version="0.2.0",
    description="API de orquestração para separação de fontes e análise musical.",
)

MAX_UPLOAD_BYTES = 250 * 1024 * 1024
ALLOWED_SUFFIXES = {".mp3", ".wav", ".flac", ".m4a", ".ogg"}
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/data/uploads"))
Base.metadata.create_all(bind=engine)


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
    error_code: Optional[str] = None
    error_message: Optional[str] = None


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
    original_name = audio.filename or "audio"
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
            job = AnalysisJob(
                id=job_id,
                status=JobStatus.queued.value,
                original_filename=Path(original_name).name,
                audio_path=str(destination),
                created_at=created_at,
            )
            db.add(job)
            db.commit()
        process_analysis.delay(job_id)
        return JobAccepted(
            job_id=job_id,
            status=JobStatus.queued,
            created_at=created_at,
            message="Áudio armazenado e tarefa enviada à fila de processamento.",
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
            error_code=job.error_code,
            error_message=job.error_message,
        )
