# app/models.py
import uuid
from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    Text,
    Integer,
    Enum as SQLEnum,
    Index,
    Boolean,
)
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import relationship
from app.database import Base


class ProcessStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AuditResult(str, Enum):
    PASSED = "PASSED"
    VIOLATION = "VIOLATION"
    WARNING = "WARNING"


class UserRole(str, Enum):
    VIEWER = "viewer"
    UPLOADER = "uploader"
    REVIEWER = "reviewer"
    ADMIN = "admin"


# ─────────────────────────────────────────────
#  Users
# ─────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(SQLEnum(UserRole), default=UserRole.UPLOADER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    documents = relationship("Document", back_populates="uploader")
    refresh_tokens = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )


# ─────────────────────────────────────────────
#  Refresh Tokens (stored for rotation + revocation)
# ─────────────────────────────────────────────
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash = Column(
        String(128), nullable=False, unique=True
    )  # store hash, not raw token
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    ip_address = Column(INET, nullable=True)

    user = relationship("User", back_populates="refresh_tokens")

    __table_args__ = (
        Index("idx_refresh_tokens_user_id", "user_id"),
        Index("idx_refresh_tokens_token_hash", "token_hash"),
    )


# ─────────────────────────────────────────────
#  Documents
# ─────────────────────────────────────────────
class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False)  # original user filename (sanitised)
    secure_filename = Column(
        String(255), nullable=False, unique=True
    )  # random token name on disk
    file_path = Column(String(512), nullable=False)
    sha256 = Column(String(64), nullable=False, unique=True)  # dedup + integrity
    mime_type = Column(String(64), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    status = Column(
        SQLEnum(ProcessStatus), default=ProcessStatus.PENDING, nullable=False
    )
    error_message = Column(Text, nullable=True)  # last failure reason
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    ip_address = Column(INET, nullable=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # soft delete

    uploader = relationship("User", back_populates="documents")
    logs = relationship(
        "AuditLog", back_populates="document", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_documents_status", "status"),
        Index("idx_documents_uploaded_by", "uploaded_by"),
        Index("idx_documents_sha256", "sha256"),
        Index("idx_documents_deleted_at", "deleted_at"),
    )


# ─────────────────────────────────────────────
#  Audit Logs
# ─────────────────────────────────────────────
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    rule_checked = Column(String(255), nullable=False)
    result = Column(SQLEnum(AuditResult), nullable=False)  # typed enum, not free Text
    findings = Column(Text, nullable=False)
    severity = Column(String(50), nullable=True)  # LOW / MEDIUM / HIGH / CRITICAL
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    document = relationship("Document", back_populates="logs")

    __table_args__ = (
        Index("idx_audit_logs_document_id", "document_id"),
        Index("idx_audit_logs_result", "result"),
    )
