# app/tasks.py
import asyncio
import structlog
from sqlalchemy.future import select
from app.celery_app import celery_app
from app.database import AsyncSessionLocal
from app.models import Document, AuditLog, ProcessStatus
from app.config import settings
from app.utils.document_parser import extract_text
from app.utils.audit_engine import run_all_rules

log = structlog.get_logger()


@celery_app.task(
    bind=True,
    name="app.tasks.process_document_pipeline",
    max_retries=3,
    default_retry_delay=30,
)
def process_document_pipeline(self, document_id: str):
    log.info("task_started", document_id=document_id, attempt=self.request.retries + 1)
    try:
        asyncio.run(_run_pipeline(document_id))
    except Exception as exc:
        log.error("task_failed", document_id=document_id, error=str(exc))
        raise self.retry(exc=exc)


async def _run_pipeline(document_id: str):
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Document)
            .where(Document.id == document_id)
            .with_for_update(skip_locked=True)
        )
        doc = result.scalar_one_or_none()

        if not doc:
            log.warning("document_not_found", document_id=document_id)
            return

        if doc.status not in (ProcessStatus.PENDING, ProcessStatus.FAILED):
            log.info("document_already_processed", document_id=document_id, status=doc.status)
            return

        # Mark as processing
        doc.status = ProcessStatus.PROCESSING
        doc.error_message = None
        await db.commit()
        log.info("pipeline_processing", document_id=document_id)

        try:
            # Read file
            with open(doc.file_path, "rb") as f:
                content = f.read()

            # Extract text
            text = extract_text(content, doc.mime_type, doc.filename)
            if not text.strip():
                text = "Document appears to be empty or unreadable."
            log.info("text_extracted", document_id=document_id, chars=len(text))

            # Run audit rules
            audit_results = run_all_rules(
                text=text,
                gemini_api_key=settings.GEMINI_API_KEY.get_secret_value(),
            )
            log.info("rules_evaluated", document_id=document_id, count=len(audit_results))

            # Save results
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
            log.info("pipeline_complete", document_id=document_id, rules=len(audit_results))

        except Exception as e:
            doc.status = ProcessStatus.FAILED
            doc.error_message = str(e)[:500]
            await db.commit()
            log.error("pipeline_failed", document_id=document_id, error=str(e))
            raise