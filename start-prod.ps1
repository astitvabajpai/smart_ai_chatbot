$env:PYTHONUNBUFFERED = "1"

# Create required directories
@("logs", "storage/uploads", "storage/chroma") | ForEach-Object {
    if (-not (Test-Path $_)) {
        New-Item -ItemType Directory -Path $_ -Force | Out-Null
    }
}

# Log startup info
Write-Host "🚀 Starting Document Chatbot API..."
Write-Host "   Environment: $env:APP_ENV"
Write-Host "   Workers: $($env:API_WORKERS -or 4)"
Write-Host "   Port: $($env:API_PORT -or 8000)"
Write-Host "   Vector Backend: $($env:VECTOR_BACKEND -or 'chroma')"

# Start Gunicorn with Uvicorn workers
$workers = if ($env:API_WORKERS) { $env:API_WORKERS } else { 4 }
$host_addr = if ($env:API_HOST) { $env:API_HOST } else { "0.0.0.0" }
$port = if ($env:API_PORT) { $env:API_PORT } else { 8000 }

gunicorn `
    -k uvicorn.workers.UvicornWorker `
    -w $workers `
    -b "$($host_addr):$port" `
    --access-logfile logs/access.log `
    --error-logfile logs/error.log `
    --log-level "$($env:LOG_LEVEL -or 'info')" `
    --timeout 120 `
    --graceful-timeout 30 `
    --keep-alive 5 `
    app.main:app
