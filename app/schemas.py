from pydantic import BaseModel, EmailStr, UUID4, Field, field_validator
from typing import Optional, List
from datetime import datetime
from app.models import ProcessStatus, AuditResult, UserRole
import re

# ─────────────────────────────────────────────
#  Auth Schemas
# ─────────────────────────────────────────────
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: Optional[str] = Field(default=None, max_length=255)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[^a-zA-Z0-9]", v):
            raise ValueError("Password must contain at least one special character")
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class RefreshRequest(BaseModel):
    refresh_token: str

class UserResponse(BaseModel):
    id: UUID4
    email: EmailStr
    full_name: Optional[str]
    role: UserRole
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}

# ─────────────────────────────────────────────
#  Document Schemas
# ─────────────────────────────────────────────
class DocumentResponse(BaseModel):
    document_id: UUID4 = Field(..., alias="id")
    filename: str
    status: ProcessStatus
    mime_type: str
    file_size_bytes: int
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None

    model_config = {"from_attributes": True, "populate_by_name": True}

class DocumentStatusResponse(BaseModel):
    document_id: UUID4 = Field(..., alias="id")
    status: ProcessStatus
    updated_at: datetime
    error_message: Optional[str] = None

    model_config = {"from_attributes": True, "populate_by_name": True}

# ─────────────────────────────────────────────
#  Audit Log Schemas
# ─────────────────────────────────────────────
class AuditLogResponse(BaseModel):
    id: UUID4
    document_id: UUID4
    rule_checked: str
    result: AuditResult
    findings: str
    severity: Optional[str]
    created_at: datetime
    model_config = {"from_attributes": True}

class AuditReportResponse(BaseModel):
    document_id: UUID4
    filename: str
    status: ProcessStatus
    total_checks: int
    passed: int
    violations: int
    warnings: int
    logs: List[AuditLogResponse]
    ai_findings: List[AuditLogResponse] = []

# ─────────────────────────────────────────────
#  Pagination
# ─────────────────────────────────────────────
class PaginatedDocuments(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[DocumentResponse]