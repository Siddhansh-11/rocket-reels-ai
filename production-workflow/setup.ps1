# Check if Docker is installed and running
$dockerRunning = $false
try {
    docker info | Out-Null
    $dockerRunning = $true
    Write-Host "✅ Docker is running correctly" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker is not running or not installed!" -ForegroundColor Red
    Write-Host "Please install Docker Desktop from: https://www.docker.com/products/docker-desktop/" -ForegroundColor Yellow
    exit 1
}

# Create directories
Write-Host "📁 Creating required directories..." -ForegroundColor Cyan
New-Item -Path "credentials" -ItemType Directory -Force | Out-Null
New-Item -Path "output" -ItemType Directory -Force | Out-Null

# Check for .env file
if (-not (Test-Path ".env")) {
    Write-Host "⚠️ Creating .env file template. Please fill in your API keys!" -ForegroundColor Yellow
    Copy-Item ".env.example" ".env" -ErrorAction SilentlyContinue
    if (-not (Test-Path ".env")) {
        # Create minimal .env if example doesn't exist
        @"
# Required API Keys
DEEPSEEK_API_KEY=your_deepseek_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key
"@ | Out-File -FilePath ".env"
    }
    Write-Host "📝 Please edit the .env file with your API keys before continuing" -ForegroundColor Yellow
    notepad ".env"
    Read-Host "Press Enter after you've updated the .env file"
}

# Build the Docker image
Write-Host "🔨 Building Docker image..." -ForegroundColor Cyan
docker-compose build

Write-Host "🚀 Setup complete! Run the application with:" -ForegroundColor Green
Write-Host "docker-compose run rocket-reels-ai ""AI topic of interest""" -ForegroundColor Cyan