Param(
    [switch]$Build
)

$projectRoot = Split-Path -Parent $PSScriptRoot
$linuxRoot = '/mnt/c/Users/paulo.laredo/Documents/projetos/pessoal/trade'
$composeCommand = if ($Build) { 'docker compose up -d --build --remove-orphans' } else { 'docker compose up -d --remove-orphans' }

Write-Host 'Starting WSL Docker and Trade AI stack...'
wsl -d Ubuntu -u root -e bash -lc "systemctl start docker"
if ($LASTEXITCODE -ne 0) {
    throw 'Could not start the Docker daemon inside WSL.'
}
wsl -d Ubuntu -e bash -lc "cd $linuxRoot && $composeCommand"
if ($LASTEXITCODE -ne 0) {
    throw 'Could not start the WSL Docker stack. Run scripts/diagnose_stack.sh and inspect the generated report.'
}

Write-Host 'Checking published endpoints...'
wsl -d Ubuntu -e bash -lc "cd $linuxRoot && curl --fail --silent --show-error http://127.0.0.1:8001/api/health"
if ($LASTEXITCODE -ne 0) {
    throw 'Backend did not become healthy. Run scripts/diagnose_stack.sh for the centralized report.'
}

Write-Host 'Trade AI stack is available at http://localhost:4173'