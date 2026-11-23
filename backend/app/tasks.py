from datetime import datetime, timezone
from .celery_app import celery_app
from .database import SessionLocal
from .models import AnalysisJob

@celery_app.task(name="app.tasks.process_analysis", bind=True, max_retries=0)
def process_analysis(self, job_id: str):
    with SessionLocal() as db:
        job = db.get(AnalysisJob, job_id)
        if job is None:
            return {"job_id": job_id, "status": "not_found"}
        job.status = "processing"
        job.message = "Worker recebeu a tarefa."
        db.commit()

        # Ponto de integração intencional: ainda não há modelo de inferência aprovado.
        # Falhar explicitamente evita indicar ao usuário que houve análise real.
        job.status = "failed"
        job.error_code = "INFERENCE_PIPELINE_NOT_CONFIGURED"
        job.error_message = (
            "Infraestrutura de fila ativa, mas os modelos de separação, "
            "transcrição e reconhecimento harmônico ainda não foram integrados."
        )
        job.message = "Tarefa recebida; aguardando integração dos modelos de áudio."
        db.commit()
        return {
            "job_id": job_id,
            "status": job.status,
            "error_code": job.error_code,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
