import asyncio
import structlog
import traceback
from sqlalchemy.future import select
from app.celery_app import celery_app
from app.database import AsyncSessionLocal
from app.models import Document, AuditLog, ProcessStatus
from app.config import settings
from app.utils.document_parser import extract_text
from app.utils.audit_engine import run_all_rules
from pathlib import Path

log = structlog.get_logger()

async def process_document(document_id: str):
    await _run_pipeline(document_id)

@celery_app.task(
    bind=True,
    name="app.tasks.process_document_pipeline",
    max_retries=3,
    default_retry_delay=30,
)
def process_document_pipeline(self, document_id: str):
    log.info("task_started", document_id=document_id, attempt=self.request.retries + 1)
    try:
        asyncio.run(process_document(document_id))
    except Exception as exc:
        # Log the full stack trace for better debugging
        log.error("task_critical_failure", 
                  document_id=document_id, 
                  error=str(exc), 
                  traceback=traceback.format_exc())
        raise self.retry(exc=exc)

async def _run_pipeline(document_id: str):
    async with AsyncSessionLocal() as db:
        # 1. Fetch document
        result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        doc = result.scalar_one_or_none()

        if not doc:
            log.warning("document_not_found", document_id=document_id)
            return

        # 2. Status Guard
        if doc.status not in (ProcessStatus.PENDING, ProcessStatus.FAILED):
            log.info("document_already_processed", document_id=document_id, status=doc.status)
            return

        doc.status = ProcessStatus.PROCESSING
        await db.commit()
        
        try:
            # 3. File access
            file_path = Path(doc.file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"File not found at {file_path}")

            with open(file_path, "rb") as f:
                content = f.read()

            text = extract_text(content, doc.mime_type, doc.filename)
            log.info("text_extracted", document_id=document_id, char_count=len(text))

            # 4. Gemini Key Check
            api_key = settings.GEMINI_API_KEY.get_secret_value()
            if not api_key or len(api_key) < 10:
                raise ValueError("GEMINI_API_KEY is missing or invalid.")

            # 5. Audit Execution
            audit_results = run_all_rules(text=text, gemini_api_key=api_key)
            
            # 6. Save Logs
            for r in audit_results:
                log_entry = AuditLog(
                    document_id=doc.id,
                    rule_checked=r["rule"],
                    result=r["result"],
                    findings=r["findings"],
                    severity=r.get("severity", "LOW"),
                )
                db.add(log_entry)

            doc.status = ProcessStatus.COMPLETED
            await db.commit()
            log.info("pipeline_complete", document_id=document_id)

        except Exception as e:
            # Catching and logging the specific failure
            log.error("pipeline_step_failed", 
                      document_id=document_id, 
                      error_type=type(e).__name__, 
                      error_message=str(e))
            
            doc.status = ProcessStatus.FAILED
            doc.error_message = f"{type(e).__name__}: {str(e)}"[:500]
            await db.commit()
            raise # Re-raise so Celery knows to retry