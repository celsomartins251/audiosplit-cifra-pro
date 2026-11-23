from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

app = FastAPI(
    title="AudioSplit & Cifra Pro API",
    version="0.1.0",
    description="API de orquestração para separação de fontes e análise musical.",
)

MAX_UPLOAD_BYTES = 250 * 1024 * 1024
ALLOWED_SUFFIXES = {".mp3", ".wav", ".flac", ".m4a", ".ogg"}


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
    filename = (audio.filename or "").lower()
    suffix = "." + filename.rsplit(".", 1)[-1] if "." in filename else ""
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=415, detail="Formato não suportado.")
    content = await audio.read(MAX_UPLOAD_BYTES + 1)
    if not content:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Arquivo excede o limite temporário de 250 MB.")
    # A persistência e a fila de processamento serão conectadas na próxima etapa.
    # Não retornar sucesso de inferência enquanto não houver worker real.
    return JobAccepted(
        job_id=str(uuid4()),
        status=JobStatus.queued,
        created_at=datetime.now(timezone.utc),
        message="Recebimento validado em modo inicial; fila e armazenamento ainda não conectados.",
    )


@app.get("/v1/jobs/{job_id}")
async def get_job(job_id: str):
    raise HTTPException(
        status_code=501,
        detail="Consulta de jobs será habilitada quando a persistência e o worker forem integrados.",
    )
