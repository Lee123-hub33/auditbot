# AuditBot

An intelligent document auditing API that automatically reviews uploaded documents against configurable compliance rules and AI-powered semantic analysis. Upload a PDF or TXT file and get back a structured report of violations, warnings, and passed checks.

---

## What it does

AuditBot accepts document uploads via a secure REST API, processes them asynchronously through a rule engine, and returns detailed audit reports. Every document goes through two layers of analysis:

- **Local rules** — fast regex and heuristic checks (PII detection, prohibited terms, sensitive keywords, URL counts, document length)
- **Gemini AI analysis** — deep semantic review checking compliance language, completeness, clarity, risk indicators, and data handling practices

---

## Tech stack

| Layer | Technology |
|---|---|
| API | FastAPI + Uvicorn |
| Database | PostgreSQL 15 + SQLAlchemy (async) |
| Task queue | Celery + Redis |
| Auth | JWT RS256 (access + refresh tokens) |
| Migrations | Alembic |
| AI | Google Gemini 1.5 Flash |
| Logging | structlog (JSON) |
| Rate limiting | slowapi (Redis-backed) |
| Task monitor | Flower |

---

## Project structure

```
auditbot/
├── .env.example                  ← copy to .env and fill in values
├── .gitignore
├── requirements.txt
├── generate_keys.py              ← run once to create JWT keypair
├── generate_certs.py             ← run once to create SSL certs (dev)
├── start.ps1                     ← Windows: starts all services at once
├── alembic.ini
├── Dockerfile
├── docker-compose.yml
├── nginx/
│   └── nginx.conf                ← rate limiting, HTTPS, reverse proxy
├── certs/                        ← SSL certs (git-ignored)
├── secrets/                      ← JWT keys (git-ignored)
├── storage/                      ← uploaded files (git-ignored)
├── tests/
│   └── test_auth.py
└── app/
    ├── config.py                 ← all settings, loaded from .env
    ├── database.py               ← async SQLAlchemy engine
    ├── models.py                 ← User, Document, AuditLog, RefreshToken
    ├── schemas.py                ← Pydantic request/response models
    ├── celery_app.py             ← Celery factory and config
    ├── tasks.py                  ← document processing pipeline
    ├── main.py                   ← app factory, middleware, routers
    ├── seed_admin.py             ← creates first admin user
    ├── auth/
    │   ├── jwt.py                ← token creation and verification
    │   └── rbac.py               ← role hierarchy and route guards
    ├── middleware/
    │   ├── logging.py            ← request logging with correlation IDs
    │   └── security_headers.py  ← security response headers
    ├── routers/
    │   ├── auth.py               ← register, login, refresh, logout, /me
    │   ├── documents.py          ← upload, list, status, delete
    │   └── audit.py              ← report and log retrieval
    └── utils/
        ├── file_validator.py     ← magic-byte validation, SHA-256
        ├── document_parser.py    ← PDF and TXT text extraction
        └── audit_engine.py       ← local rules + Gemini AI analysis
```

---

## Prerequisites

- Python 3.11+
- PostgreSQL 15
- Redis 7 (via Docker recommended on Windows)
- Docker (for Redis on Windows)
- A Google Gemini API key — get one free at [aistudio.google.com](https://aistudio.google.com)

---

## Setup

### 1. Clone and open in VS Code

```bash
git clone <your-repo-url>
cd auditbot
code .
```

### 2. Create virtual environment

```powershell
# Windows
python -m venv env
.\env\Scripts\Activate.ps1

# Mac/Linux
python3 -m venv env
source env/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
pip install "pydantic[email]" "bcrypt==4.0.1"
```

On Windows also install:
```bash
pip install python-magic-bin
```

### 4. Generate JWT signing keys

Run once. Creates `secrets/jwt_private.pem` and `secrets/jwt_public.pem`.

```bash
python generate_keys.py
```

### 5. Generate SSL certificates (development only)

Run once. Creates `certs/cert.pem` and `certs/key.pem`.

```bash
pip install cryptography
python generate_certs.py
```

> For production, replace these with real certs from [Let's Encrypt](https://letsencrypt.org).

### 6. Configure environment

```bash
cp .env.example .env
```

Open `.env` and fill in:

```dotenv
DATABASE_URL=postgresql+asyncpg://auditbot_app:yourpassword@localhost:5432/audit_db
DATABASE_URL_SYNC=postgresql://auditbot_app:yourpassword@localhost:5432/audit_db
REDIS_URL=redis://localhost:6379/0
GEMINI_API_KEY=your_gemini_api_key_here
SECRET_KEY=run_this_to_generate: python -c "import secrets; print(secrets.token_hex(64))"
ALLOWED_ORIGINS=["http://localhost:3000"]
```

### 7. Set up PostgreSQL

Create the database and user (run in pgAdmin or psql):

```sql
CREATE USER auditbot_app WITH PASSWORD 'yourpassword';
CREATE DATABASE audit_db OWNER auditbot_app;
GRANT ALL PRIVILEGES ON DATABASE audit_db TO auditbot_app;
GRANT ALL ON SCHEMA public TO auditbot_app;
```

### 8. Start Redis (Windows via Docker)

```bash
docker run -d --name auditbot_redis -p 6379:6379 redis:7-alpine
```

### 9. Run database migrations

```bash
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

### 10. Create admin user

```bash
python -m app.seed_admin
```

Default admin credentials:
- Email: `admin@auditbot.com`
- Password: `Admin@2026`

> Change these immediately in `app/seed_admin.py` before running in production.

---

## Running

### Option A — One command (Windows)

```powershell
.\start.ps1
```

This starts Redis, the Celery worker, Flower, and the API automatically.

### Option B — Manual (three terminals)

**Terminal 1 — API:**
```bash
uvicorn app.main:app --reload
```

**Terminal 2 — Celery worker:**
```bash
celery -A app.celery_app worker --pool=solo -Q documents -l info
```

**Terminal 3 — Flower task monitor (optional):**
```bash
celery -A app.celery_app flower --port=5555
```

---

## API endpoints

| Method | Endpoint | Role required | Description |
|--------|----------|--------------|-------------|
| POST | `/api/v1/auth/register` | None | Register new user |
| POST | `/api/v1/auth/login` | None | Login, receive tokens |
| POST | `/api/v1/auth/refresh` | None | Refresh access token |
| POST | `/api/v1/auth/logout` | None | Revoke refresh token |
| GET | `/api/v1/auth/me` | Any | Current user profile |
| PATCH | `/api/v1/auth/users/{id}/role` | Admin | Change user role |
| POST | `/api/v1/documents/upload` | Uploader+ | Upload document for audit |
| GET | `/api/v1/documents` | Viewer+ | List documents |
| GET | `/api/v1/documents/{id}/status` | Viewer+ | Check processing status |
| DELETE | `/api/v1/documents/{id}` | Uploader+ | Soft delete document |
| GET | `/api/v1/audit/{id}/report` | Reviewer+ | Full audit report |
| GET | `/api/v1/audit/{id}/logs` | Reviewer+ | Individual audit log entries |
| GET | `/health` | None | Health check |

**Interactive docs:** `http://localhost:8000/docs`

---

## User roles

| Role | Can do |
|---|---|
| `viewer` | Check document status, view their own documents |
| `uploader` | Everything viewer can do + upload and delete documents |
| `reviewer` | Everything uploader can do + view audit reports and logs |
| `admin` | Full access including managing all users and all documents |

---

## Audit report example

```json
{
  "document_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "filename": "contract.pdf",
  "status": "COMPLETED",
  "total_checks": 10,
  "passed": 7,
  "violations": 2,
  "warnings": 1,
  "logs": [
    {
      "rule_checked": "PII Detection",
      "result": "VIOLATION",
      "findings": "Possible SSN detected (format: XXX-XX-XXXX)",
      "severity": "HIGH"
    },
    {
      "rule_checked": "RISK_INDICATORS",
      "result": "VIOLATION",
      "findings": "Document contains clauses that expose significant financial liability",
      "severity": "CRITICAL"
    },
    {
      "rule_checked": "COMPLIANCE_LANGUAGE",
      "result": "PASSED",
      "findings": "Document uses appropriate legal and compliance language",
      "severity": "LOW"
    }
  ]
}
```

---

## Customising audit rules

### Adding a local rule

Open `app/utils/audit_engine.py` and add a new function:

```python
def check_your_rule(text: str) -> Dict[str, Any]:
    if "your trigger term" in text.lower():
        return {
            "rule": "Your Rule Name",
            "result": AuditResult.VIOLATION,
            "findings": "Describe what was found",
            "severity": "HIGH",  # LOW, MEDIUM, HIGH, or CRITICAL
        }
    return {
        "rule": "Your Rule Name",
        "result": AuditResult.PASSED,
        "findings": "All clear",
        "severity": "LOW",
    }
```

Then add it to the `local_rules` list in `run_all_rules`:

```python
local_rules = [
    check_pii_presence,
    check_document_length,
    check_prohibited_terms,
    check_url_presence,
    check_sensitive_keywords,
    check_your_rule,  # ← add here
]
```

### Changing AI rules

Edit the numbered rules in the `run_gemini_audit` prompt inside `audit_engine.py`:

```python
prompt = f"""...
1. CONTRACT_TERMS: Does the document include all required contract terms?
2. PAYMENT_CLAUSES: Are payment terms clearly defined and fair?
3. LIABILITY_CAPS: Does the document include liability limitation clauses?
4. TERMINATION_CLAUSES: Are termination conditions clearly stated?
5. GOVERNING_LAW: Is the governing law and jurisdiction specified?
..."""
```

Gemini will audit every document against these rules automatically.

---

## Security features

- JWT RS256 asymmetric tokens (15-min access + 7-day rotating refresh)
- Role-based access control on every endpoint
- Magic-byte file validation (not just extension)
- SHA-256 deduplication
- SQL injection prevention via SQLAlchemy ORM
- Rate limiting per IP (Redis-backed, shared across replicas)
- Structured JSON logging with correlation IDs
- Soft delete (audit trail preserved)
- No credentials in version control

---

## Production checklist

- [ ] Replace self-signed certs with Let's Encrypt
- [ ] Set `ENVIRONMENT=production` in `.env`
- [ ] Change default admin password in `seed_admin.py`
- [ ] Deploy to a VPS (DigitalOcean, AWS, Azure)
- [ ] Point a domain to the server
- [ ] Set `ALLOWED_ORIGINS` to your real domain
- [ ] Back up `secrets/` and `certs/` securely

---

## Running tests

```bash
pytest tests/ -v
```

---

## Monitoring

| Service | URL |
|---|---|
| API docs | http://localhost:8000/docs |
| Health check | http://localhost:8000/health |
| Flower (tasks) | http://localhost:5555 |