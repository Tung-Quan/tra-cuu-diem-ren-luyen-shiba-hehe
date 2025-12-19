# Build frontend and run backend
# PowerShell script

Write-Host "🔨 Building Frontend..." -ForegroundColor Cyan
Set-Location frontend
npm install
npm run build
Set-Location ..

Write-Host "✅ Frontend built successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "🚀 Starting Backend with Frontend..." -ForegroundColor Cyan
Write-Host "   Backend API: http://localhost:8000/docs" -ForegroundColor Yellow
Write-Host "   Frontend UI: http://localhost:8000" -ForegroundColor Yellow
Write-Host ""

python -m backend.main_refactored
