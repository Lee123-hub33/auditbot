# AuditBot — Production Setup Guide (PyCharm)

## Prerequisites
- Python 3.11+
- PostgreSQL 15
- Redis 7
- Docker + Docker Compose (optional, for full stack)

---

## Step 1 — Clone & open in PyCharm
Open the project folder in PyCharm. It will detect `requirements.txt` automatically.

## Step 2 — Create virtual environment
In PyCharm: `Settings → Project → Python Interpreter → Add → Virtualenv`
Or in terminal:
```bash
python -m venv .venv
source .venv/bin/activate        # Mac/Linux
.venv\Scripts\activate           # Windows
pip install -r requirements.txt
```

## Step 3 — Generate JWT keys
```bash
python generate_keys.py
# Creates: secrets/jwt_private.pem  secrets/jwt_public.pem
```

## Step 4 — Configure environment
```bash
cp .env.example .env
# Edit .env with your PostgreSQL, Redis, and Gemini credentials
```

## Step 5 — Create database & run migrations
```bash
# Make sure PostgreSQL is running, then:
alembic upgrade head
```

## Step 6 — Run the API (PyCharm Run Configuration)
Create a PyCharm Run Configuration:
- **Script**: `uvicorn`
- **Parameters**: `app.main:app --reload --host 0.0.0.0 --port 8000`
- **Working directory**: project root

Or from terminal:
```bash
uvicorn app.main:app --reload
```

## Step 7 — Run Celery worker (second terminal)
```bash
celery -A app.celery_app worker -Q documents --concurrency=2 -l info
```

## Step 8 — (Optional) Run Flower task monitor
```bash
celery -A app.celery_app flower --port=5555
# Open: http://localhost:5555
```

---

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/auth/register` | None | Register new user |
| POST | `/api/v1/auth/login` | None | Login, get tokens |
| POST | `/api/v1/auth/refresh` | None | Refresh access token |
| POST | `/api/v1/auth/logout` | None | Revoke refresh token |
| GET  | `/api/v1/auth/me` | Bearer | Current user info |
| POST | `/api/v1/documents/upload` | uploader+ | Upload document |
| GET  | `/api/v1/documents` | viewer+ | List documents |
| GET  | `/api/v1/documents/{id}/status` | viewer+ | Check status |
| DELETE | `/api/v1/documents/{id}` | uploader+ | Soft delete |
| GET  | `/api/v1/audit/{id}/report` | reviewer+ | Full audit report |
| GET  | `/api/v1/audit/{id}/logs` | reviewer+ | Audit log entries |
| GET  | `/health` | None | Health check |

Interactive docs (dev only): http://localhost:8000/docs

---

## Full Docker stack
```bash
echo "your_db_password" > secrets/db_password.txt
docker-compose up --build
```

## Run tests
```bash
pytest tests/ -v
```
