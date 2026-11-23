"""Real first-pass audio pipeline: Demucs stems, vocal ASR and chord estimates."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from faster_whisper import WhisperModel

from .chord_recognition import recognize_chords

DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
MODEL_DIR = Path(os.getenv("MODEL_DIR", "/models"))
SEPARATION_MODEL = os.getenv("DEMUCS_MODEL", "htdemucs_ft")
ASR_MODEL = os.getenv("WHISPER_MODEL", "small")
ASR_LANGUAGE = os.getenv("ASR_LANGUAGE", "pt")
_asr = None

def _get_asr():
    global _asr
    if _asr is None:
        device = os.getenv("WHISPER_DEVICE", "cpu")
        compute_type = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
        _asr = WhisperModel(ASR_MODEL, device=device, compute_type=compute_type, download_root=str(MODEL_DIR / "whisper"))
    return _asr

def _run_demucs(input_path: Path, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable, "-m", "demucs",
        "-n", SEPARATION_MODEL,
        "--out", str(output_dir),
        "--shifts", os.getenv("DEMUCS_SHIFTS", "1"),
        str(input_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=int(os.getenv("SEPARATION_TIMEOUT", "7200")))
    if completed.returncode != 0:
        raise RuntimeError("Demucs falhou: " + (completed.stderr[-1800:] or completed.stdout[-1800:]))
    stem_dir = output_dir / SEPARATION_MODEL / input_path.stem
    if not stem_dir.is_dir():
        raise RuntimeError("O Demucs terminou sem produzir a pasta de stems esperada.")
    stems = {}
    for name in ("vocals", "drums", "bass", "other"):
        path = stem_dir / f"{name}.wav"
        if path.exists():
            stems[name] = str(path)
    if len(stems) < 4:
        raise RuntimeError("Separação incompleta: não foram encontrados os quatro stems esperados.")
    return stems

def _transcribe(vocal_path: str):
    model = _get_asr()
    segments, info = model.transcribe(
        vocal_path,
        language=ASR_LANGUAGE,
        beam_size=5,
        word_timestamps=True,
        vad_filter=False,
        condition_on_previous_text=False,
    )
    words = []
    for segment in segments:
        if segment.words:
            for word in segment.words:
                token = (word.word or "").strip()
                if token:
                    words.append({
                        "start": round(float(word.start), 3),
                        "end": round(float(word.end), 3),
                        "label": token,
                        "confidence": round(float(word.probability), 3) if word.probability is not None else None,
                        "source": f"faster-whisper-{ASR_MODEL}",
                    })
        elif segment.text.strip():
            words.append({
                "start": round(float(segment.start), 3),
                "end": round(float(segment.end), 3),
                "label": segment.text.strip(),
                "confidence": None,
                "source": f"faster-whisper-{ASR_MODEL}-segment",
            })
    return {"language": info.language, "language_probability": info.language_probability, "words": words}

def run_pipeline(job_id: str, source_path: str, progress_callback):
    job_dir = DATA_DIR / "jobs" / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    source = Path(source_path)
    progress_callback(8, "Preparando áudio e iniciando separação")
    stems = _run_demucs(source, job_dir / "separated")
    progress_callback(55, "Separação concluída; transcrevendo voz")
    transcription = _transcribe(stems["vocals"])
    progress_callback(76, "Transcrição concluída; analisando harmonia")
    chords = recognize_chords(source_path)
    progress_callback(94, "Organizando resultados e metadados")
    stem_result = {}
    for name, path in stems.items():
        target = job_dir / f"{name}.wav"
        if Path(path) != target:
            target.write_bytes(Path(path).read_bytes())
        stem_result[name] = {
            "filename": target.name,
            "download_path": f"/v1/jobs/{job_id}/stems/{name}",
        }
    result = {
        "schema_version": "1.0",
        "job_id": job_id,
        "separation": {
            "model": SEPARATION_MODEL,
            "stems": stem_result,
            "source_sample": "Demucs multi-stem baseline",
        },
        "transcription": transcription,
        "chords": chords,
        "alignment_note": "Timestamps de palavra são estimativas ASR; alinhamento fonético/silábico dedicado ainda não aplicado.",
        "chord_note": "Acordes são estimativas baseline por chroma e templates; revisar manualmente, sobretudo tensões, inversões e mudanças rápidas.",
    }
    (job_dir / "result.json").write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return result
