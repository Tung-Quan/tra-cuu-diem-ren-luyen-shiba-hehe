# Development mode - Run frontend and backend separately
# PowerShell script

Write-Host "🚀 Starting Development Mode..." -ForegroundColor Cyan
Write-Host ""
Write-Host "   Backend API: http://localhost:8000/docs" -ForegroundColor Yellow
Write-Host "   Frontend Dev: http://localhost:5173" -ForegroundColor Yellow
Write-Host ""
Write-Host "⚠️  You need to run these in separate terminals:" -ForegroundColor Yellow
Write-Host "   Terminal 1: python -m backend.main_refactored" -ForegroundColor White
Write-Host "   Terminal 2: cd frontend; npm run dev" -ForegroundColor White
Write-Host ""
Write-Host "Or press Ctrl+C and run them manually." -ForegroundColor Gray
Write-Host ""

# Start backend first
python -m backend.main_refactored
