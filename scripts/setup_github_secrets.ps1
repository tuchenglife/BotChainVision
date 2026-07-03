# Read secrets from local .env and set GitHub Actions secrets (values are not printed).
$envFile = Join-Path (Join-Path $PSScriptRoot "..") ".env"
$envFile = (Resolve-Path $envFile -ErrorAction SilentlyContinue).Path
if (-not $envFile) {
    Write-Error ".env not found. Copy .env.example to .env and fill in values."
    exit 1
}

$vars = @{}
Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*([^#=]+)=(.*)$') {
        $vars[$matches[1].Trim()] = $matches[2].Trim()
    }
}

if (-not $vars['SUPABASE_URL'] -or -not $vars['SUPABASE_SERVICE_ROLE_KEY']) {
    Write-Error "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env"
    exit 1
}

Write-Host "Setting SUPABASE_URL..."
$vars['SUPABASE_URL'] | gh secret set SUPABASE_URL --body-file -

Write-Host "Setting SUPABASE_SERVICE_ROLE_KEY..."
$vars['SUPABASE_SERVICE_ROLE_KEY'] | gh secret set SUPABASE_SERVICE_ROLE_KEY --body-file -

Write-Host "Done. Verify at: https://github.com/tuchenglife/BotChainVision/settings/secrets/actions"
