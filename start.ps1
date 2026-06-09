Write-Host "Starting AuditBot..." -ForegroundColor Green

if (-not (Test-Path ".\env\Scripts\Activate.ps1")) {
    Write-Host "ERROR: Run this from the auditbot folder" -ForegroundColor Red
    exit
}

.\env\Scripts\Activate.ps1

$redis = docker ps --filter "name=auditbot_redis" --filter "status=running" -q
if (-not $redis) {
    Write-Host "Starting Redis..." -ForegroundColor Yellow
    docker start auditbot_redis 2>$null
    if ($LASTEXITCODE -ne 0) {
        docker run -d --name auditbot_redis -p 6379:6379 redis:7-alpine
    }
    Start-Sleep -Seconds 3
}
Write-Host "Redis running" -ForegroundColor Green

Write-Host "Starting Celery worker..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; .\env\Scripts\Activate.ps1; celery -A app.celery_app worker --pool=solo -Q documents -l info"

Start-Sleep -Seconds 3

Write-Host "Starting Flower..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; .\env\Scripts\Activate.ps1; celery -A app.celery_app flower --port=5555"

Start-Sleep -Seconds 2

Write-Host "API Docs:  http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "Health:    http://localhost:8000/health" -ForegroundColor Cyan
Write-Host "Flower:    http://localhost:5555" -ForegroundColor Cyan

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000