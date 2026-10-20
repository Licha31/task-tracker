$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$backend = Join-Path $repo 'backend'
$envFile = Join-Path $backend '.env'
$index = Join-Path $repo 'frontend/dist/index.html'
$database = Join-Path $backend 'payroll_tracker.db'
if (-not (Test-Path -LiteralPath $envFile)) { throw 'Missing backend/.env. Copy backend/.env.example and set local secrets.' }
if (-not (Test-Path -LiteralPath $index)) { throw 'Frontend build missing. Run npm run build in frontend/.' }
if (-not (Test-Path -LiteralPath $database)) { throw 'Database missing. Run uv run alembic upgrade head in backend/ first.' }

Get-Content -LiteralPath $envFile | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith('#')) {
        $parts = $line -split '=', 2
        if ($parts.Count -ne 2) { throw "Invalid .env line: $line" }
        [Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim().Trim('"').Trim("'"), 'Process')
    }
}
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
Set-Location -LiteralPath $backend
if (-not $args.Contains('--no-browser')) {
    Start-Job -ArgumentList 'http://127.0.0.1:8000/' -ScriptBlock {
        param($url)
        for ($i = 0; $i -lt 30; $i++) {
            try {
                Invoke-WebRequest -Uri $url -TimeoutSec 1 | Out-Null
                Start-Process $url
                break
            } catch { Start-Sleep -Seconds 1 }
        }
    } | Out-Null
}
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
