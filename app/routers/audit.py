# app/routers/audit.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.models import Document, AuditLog, AuditResult
from app.schemas import AuditLogResponse, AuditReportResponse
from app.auth.rbac import require_reviewer
from app.auth.jwt import get_current_user
from uuid import UUID
from typing import Optional

router = APIRouter(prefix="/api/v1/audit", tags=["Audit"])


@router.get(
    "/{document_id}/report",
    response_model=AuditReportResponse,
    dependencies=[Depends(require_reviewer)],
)
async def get_audit_report(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Full audit report for a document:
    - Summary counts (passed / violations / warnings)
    - All individual rule findings
    """
    # Fetch document
    doc_result = await db.execute(
        select(Document).where(Document.id == document_id, Document.deleted_at == None)
    )
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Non-reviewers can only see their own
    if current_user.get("role") not in ("reviewer", "admin"):
        if str(doc.uploaded_by) != current_user["sub"]:
            raise HTTPException(status_code=403, detail="Access denied")

    # Fetch audit logs
    logs_result = await db.execute(
        select(AuditLog)
        .where(AuditLog.document_id == document_id)
        .order_by(AuditLog.created_at.asc())
    )
    logs = logs_result.scalars().all()

    # Build summary counts
    passed = sum(1 for log in logs if log.result == AuditResult.PASSED)
    violations = sum(1 for log in logs if log.result == AuditResult.VIOLATION)
    warnings = sum(1 for log in logs if log.result == AuditResult.WARNING)

    return AuditReportResponse(
        document_id=doc.id,
        filename=doc.filename,
        status=doc.status,
        total_checks=len(logs),
        passed=passed,
        violations=violations,
        warnings=warnings,
        logs=logs,
    )


@router.get(
    "/{document_id}/logs",
    response_model=list[AuditLogResponse],
    dependencies=[Depends(require_reviewer)],
)
async def get_audit_logs(
    document_id: UUID,
    result_filter: Optional[AuditResult] = None,
    db: AsyncSession = Depends(get_db),
):
    """List individual audit log entries for a document, with optional result filter."""
    query = select(AuditLog).where(AuditLog.document_id == document_id)
    if result_filter:
        query = query.where(AuditLog.result == result_filter)

    logs_result = await db.execute(query.order_by(AuditLog.created_at.asc()))
    return logs_result.scalars().all()
