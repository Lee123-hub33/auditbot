FROM python:3.11-slim AS builder
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev libmagic1 build-essential && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.11-slim AS runner
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 libmagic1 && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --shell /bin/false --no-create-home appuser

COPY --from=builder /install /usr/local
WORKDIR /app
COPY --chown=appuser:appgroup . .

RUN mkdir -p /var/payload/auditbot/storage && \
    chown -R appuser:appgroup /var/payload/auditbot/storage

USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
