[CmdletBinding()]
param(
    [ValidateSet('Up', 'Status', 'Test', 'Seed', 'Admin', 'Stop')]
    [string]$Action = 'Status',
    [int]$StartupTimeoutMinutes = 40
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$linuxRepo = '/mnt/' + $repo.Substring(0, 1).ToLowerInvariant() + '/' + $repo.Substring(3).Replace('\', '/')
$linuxBase = "cd '$linuxRepo' && docker compose -p vendor-assurance-desk -f platform/ciso-assistant/docker-compose.yml -f docker/compose.override.yml"
$wslArgs = @('-d', 'Ubuntu-24.04', '-u', 'root', '--', 'bash', '-lc')

function Invoke-Wsl([string]$Command) {
    & wsl.exe @wslArgs $Command
    if ($LASTEXITCODE -ne 0) { throw "WSL command failed with exit code $LASTEXITCODE" }
}

function Invoke-Compose([string]$Arguments) {
    Invoke-Wsl "$linuxBase $Arguments"
}

function Ensure-WslKeeper {
    $pidFile = Join-Path $repo 'docker\runtime\wsl-keeper.pid'
    $alive = $false
    if (Test-Path -LiteralPath $pidFile) {
        $savedPid = 0
        [void][int]::TryParse((Get-Content -LiteralPath $pidFile -Raw).Trim(), [ref]$savedPid)
        if ($savedPid -gt 0) {
            $process = Get-CimInstance Win32_Process -Filter "ProcessId = $savedPid" -ErrorAction SilentlyContinue
            $alive = [bool]($process -and $process.CommandLine -match 'Ubuntu-24\.04.*sleep infinity')
        }
    }
    if (-not $alive) {
        $keeper = Start-Process -FilePath wsl.exe -ArgumentList @('-d', 'Ubuntu-24.04', '-u', 'root', '--', 'sleep', 'infinity') -WindowStyle Hidden -PassThru
        Set-Content -LiteralPath $pidFile -Value $keeper.Id -NoNewline
        Start-Sleep -Seconds 2
    }
}

function Stop-WslKeeper {
    $pidFile = Join-Path $repo 'docker\runtime\wsl-keeper.pid'
    if (-not (Test-Path -LiteralPath $pidFile)) { return }
    $savedPid = 0
    [void][int]::TryParse((Get-Content -LiteralPath $pidFile -Raw).Trim(), [ref]$savedPid)
    if ($savedPid -gt 0) {
        $process = Get-CimInstance Win32_Process -Filter "ProcessId = $savedPid" -ErrorAction SilentlyContinue
        if ($process -and $process.CommandLine -match 'Ubuntu-24\.04.*sleep infinity') {
            Stop-Process -Id $savedPid -Force
        }
    }
    Remove-Item -LiteralPath $pidFile -Force
}

switch ($Action) {
    'Up' {
        Ensure-WslKeeper
        Invoke-Wsl 'systemctl start docker'
        Invoke-Wsl 'docker volume inspect vendor-assurance-desk-ciso-db >/dev/null 2>&1 || docker volume create vendor-assurance-desk-ciso-db >/dev/null'
        Invoke-Compose 'up -d --no-recreate --no-deps backend qdrant'
        $deadline = (Get-Date).AddMinutes($StartupTimeoutMinutes)
        do {
            $health = ((& wsl.exe @wslArgs "docker inspect backend --format '{{.State.Health.Status}}'" 2>$null) | Out-String).Trim()
            if ($health -eq 'healthy') { break }
            Start-Sleep -Seconds 5
        } while ((Get-Date) -lt $deadline)
        if ($health -ne 'healthy') { throw "CISO Assistant backend did not become healthy within $StartupTimeoutMinutes minutes. Current health: $health. Check with -Action Status." }
        Invoke-Compose 'up -d --no-recreate'
        Invoke-Compose 'ps'
    }
    'Status' {
        Invoke-Compose 'ps'
        Invoke-Wsl 'docker version --format "client={{.Client.Version}} server={{.Server.Version}}"; docker compose version --short'
    }
    'Test' {
        Invoke-Wsl "docker exec backend python -c 'import urllib.request; r=urllib.request.urlopen(`"http://localhost:8000/api/health/`", timeout=10); print(`"backend-health=`", r.status); assert r.status == 200'"
        Invoke-Wsl 'docker exec backend python manage.py check'
        Invoke-Wsl 'docker exec backend python manage.py showmigrations tprm'
        Invoke-Wsl 'curl -kfsS -o /dev/null -w "caddy-https-status=%{http_code}\n" https://localhost:8443/'
        Invoke-Wsl 'curl -fsS -o /dev/null -w "qdrant-status=%{http_code}\n" http://127.0.0.1:6333/'
    }
    'Seed' {
        Invoke-Wsl "docker run --rm --volumes-from backend:rw -v '$linuxRepo/case-study:/input:ro' -v '$linuxRepo/scripts:/scripts:ro' alpine:3.23 sh -c 'mkdir -p /code/db/vad_data && cp /input/data.json /input/control_catalog.json /scripts/docker_seed.py /code/db/vad_data/'"
        Invoke-Wsl 'docker exec backend python /code/db/vad_data/docker_seed.py'
    }
    'Admin' {
        $privateDir = Join-Path $repo 'docker\runtime\.private'
        New-Item -ItemType Directory -Force -Path $privateDir | Out-Null
        Invoke-Wsl "docker run --rm --volumes-from backend:rw -v '$linuxRepo/scripts:/scripts:ro' alpine:3.23 sh -c 'cp /scripts/docker_admin.py /code/db/docker_admin.py'"
        Invoke-Wsl 'docker exec backend python /code/db/docker_admin.py'
        $credentialPath = Join-Path $privateDir 'admin_credentials.txt'
        Invoke-Wsl "docker run --rm --volumes-from backend:rw -v '$linuxRepo/docker/runtime/.private:/output' alpine:3.23 sh -c 'cp /code/db/admin_credentials.txt /output/admin_credentials.txt && chmod 600 /output/admin_credentials.txt'"
        if (Test-Path -LiteralPath $credentialPath) {
            $currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
            & icacls.exe $credentialPath /inheritance:r /grant:r "$($currentUser):F" 'NT AUTHORITY\SYSTEM:F' 'BUILTIN\Administrators:F' | Out-Null
        }
        "Private admin login saved to $credentialPath"
    }
    'Stop' {
        Invoke-Compose 'down'
        Stop-WslKeeper
        'Containers stopped; named data volumes are retained.'
    }
}
