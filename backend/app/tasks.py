from datetime import datetime, timezone
from .celery_app import celery_app
from .database import Base, SessionLocal, apply_sqlite_compat_migrations, engine
from .models import AnalysisJob

Base.metadata.create_all(bind=engine)
apply_sqlite_compat_migrations()
from .pipeline import run_pipeline

@celery_app.task(name="app.tasks.process_analysis", bind=True, max_retries=0)
def process_analysis(self, job_id: str):
    def update_progress(progress, message):
        with SessionLocal() as db:
            job = db.get(AnalysisJob, job_id)
            if job:
                job.progress = progress
                job.message = message
                job.updated_at = datetime.now(timezone.utc)
                db.commit()

    with SessionLocal() as db:
        job = db.get(AnalysisJob, job_id)
        if job is None:
            return {"job_id": job_id, "status": "not_found"}
        job.status = "processing"
        job.progress = 1
        job.message = "Worker iniciou o processamento."
        job.updated_at = datetime.now(timezone.utc)
        source_path = job.audio_path
        db.commit()
    try:
        import json
        result = run_pipeline(job_id, source_path, update_progress)
        with SessionLocal() as db:
            job = db.get(AnalysisJob, job_id)
            if job:
                job.status = "completed"
                job.progress = 100
                job.result_json = json.dumps(result, ensure_ascii=False)
                job.message = "Análise concluída. Revise os resultados estimados."
                job.updated_at = datetime.now(timezone.utc)
                db.commit()
        return {"job_id": job_id, "status": "completed"}
    except Exception as exc:
        with SessionLocal() as db:
            job = db.get(AnalysisJob, job_id)
            if job:
                job.status = "failed"
                job.error_code = "AUDIO_PIPELINE_FAILED"
                job.error_message = str(exc)[-3000:]
                job.message = "O processamento falhou; consulte o detalhe técnico."
                job.updated_at = datetime.now(timezone.utc)
                db.commit()
        raise
