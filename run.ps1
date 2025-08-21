# run.ps1
# Activate virtual environment and start uvicorn with reload (ignoring .venv changes)

Write-Output "Activating virtual environment..."
. .\.venv\Scripts\Activate.ps1

Write-Output "Starting FastAPI server..."
uvicorn backend.main:app --reload

