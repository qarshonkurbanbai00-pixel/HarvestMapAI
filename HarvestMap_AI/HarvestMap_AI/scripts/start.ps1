$ErrorActionPreference = 'Stop'
Set-Location "$PSScriptRoot/.."
python -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
