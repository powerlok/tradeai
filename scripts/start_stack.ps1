Param(
    [switch]$Build
)

# Start stack only if containers already exist; otherwise create them.
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$containers = @('trading_postgres','trading_redis','trading_backend','trading_ollama')
$existing = @()

$all = docker ps -a --format "{{.Names}}" | ForEach-Object { $_ }
foreach ($c in $containers) {
    if ($all -contains $c) { $existing += $c }
}

if ($existing.Count -eq $containers.Count) {
    Write-Host "All containers exist. Starting existing containers..."
    docker compose start
} else {
    Write-Host "Creating/updating stack..."
    # ensure named volume for postgres exists
    $volumes = docker volume ls --format "{{.Name}}"
    if (-not ($volumes -contains 'trade_postgres_data')) {
        Write-Host "Creating docker volume: trade_postgres_data"
        docker volume create trade_postgres_data | Out-Null
    }
    if ($Build) { docker compose up -d --build } else { docker compose up -d }
}

Write-Host "Stack is up. Use 'docker compose logs -f' to follow logs." 
