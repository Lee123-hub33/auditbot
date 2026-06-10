# app/routers/documents.py
import os
import secrets
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.database import get_db
from app.models import Document, ProcessStatus
from app.schemas import DocumentResponse, DocumentStatusResponse, PaginatedDocuments
from app.auth.rbac import require_uploader, require_viewer
from app.auth.jwt import get_current_user
from app.utils.file_validator import validate_and_read_file
from app.tasks import process_document_pipeline
from app.config import settings
from uuid import UUID
import structlog

log = structlog.get_logger()
router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])
limiter = Limiter(key_func=get_remote_address)


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_uploader)],
)
@limiter.limit("10/minute")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    content, sha256, mime_type = await validate_and_read_file(file)

    # Check for duplicate
    existing = await db.execute(select(Document).where(Document.sha256 == sha256))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409, detail="Document already uploaded (duplicate detected)"
        )

    # Safe storage path
    token = secrets.token_hex(32)
    ext = (file.filename or "file").rsplit(".", 1)[-1].lower()
    secure_name = f"{token}.{ext}"
    base = Path(settings.STORAGE_DIR).resolve()
    target = base / secure_name

    if not str(target.resolve()).startswith(str(base)):
        raise HTTPException(status_code=400, detail="Invalid file path")

    os.makedirs(base, exist_ok=True, mode=0o750)
    target.write_bytes(content)

    db_doc = Document(
        filename=os.path.basename(file.filename or "upload"),
        secure_filename=secure_name,
        file_path=str(target),
        sha256=sha256,
        mime_type=mime_type,
        file_size_bytes=len(content),
        status=ProcessStatus.PENDING,
        uploaded_by=current_user["sub"],
        ip_address=request.client.host,
    )
    db.add(db_doc)
    await db.commit()
    await db.refresh(db_doc)

    # Queue Celery task
    process_document_pipeline.apply_async(
        args=[str(db_doc.id)],
        countdown=1,
    )

    log.info(
        "document_uploaded",
        document_id=str(db_doc.id),
        filename=db_doc.filename,
        user=current_user["sub"],
    )
    return db_doc


@router.get(
    "/{document_id}/status",
    response_model=DocumentStatusResponse,
    dependencies=[Depends(require_viewer)],
)
async def get_document_status(document_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.deleted_at == None)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.get(
    "", response_model=PaginatedDocuments, dependencies=[Depends(require_viewer)]
)
async def list_documents(
    page: int = 1,
    page_size: int = 20,
    status_filter: ProcessStatus = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    page_size = min(page_size, 100)
    offset = (page - 1) * page_size

    query = select(Document).where(Document.deleted_at == None)

    if current_user.get("role") != "admin":
        query = query.where(Document.uploaded_by == current_user["sub"])

    if status_filter:
        query = query.where(Document.status == status_filter)

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar()

    docs_result = await db.execute(
        query.order_by(Document.created_at.desc()).offset(offset).limit(page_size)
    )
    docs = docs_result.scalars().all()

    return PaginatedDocuments(total=total, page=page, page_size=page_size, items=docs)


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_uploader)],
)
async def soft_delete_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    from datetime import datetime, timezone

    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.deleted_at == None)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if (
        str(doc.uploaded_by) != current_user["sub"]
        and current_user.get("role") != "admin"
    ):
        raise HTTPException(
            status_code=403, detail="Cannot delete another user's document"
        )

    doc.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    log.info(
        "document_soft_deleted", document_id=str(document_id), user=current_user["sub"]
    )
