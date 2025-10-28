# PowerShell script to activate virtual environment and run the FastAPI server

Write-Host "🚀 Starting JEE Question Generator API..." -ForegroundColor Green
Write-Host ""

# Activate virtual environment
Write-Host "📦 Activating virtual environment..." -ForegroundColor Cyan
& .\.venv\Scripts\Activate.ps1

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to activate virtual environment!" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Virtual environment activated" -ForegroundColor Green
Write-Host ""

# Run the FastAPI app
Write-Host "🌐 Starting FastAPI server on http://localhost:8000..." -ForegroundColor Cyan
Write-Host "📖 API Documentation: http://localhost:8000/docs" -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

uvicorn app:app --reload --host 0.0.0.0 --port 8000
