param(
    [string]$Executable = ".\dist\PathFlowGuard.exe"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
Set-Location $PSScriptRoot

$resolvedExecutable = (Resolve-Path $Executable).Path
$runtimeDir = Join-Path $env:TEMP ("pathflowguard-runtime-smoke-" + [guid]::NewGuid().ToString("N"))
if (Test-Path -LiteralPath $runtimeDir) {
    Remove-Item -LiteralPath $runtimeDir -Recurse -Force
}

try {
    $doctorRaw = & $resolvedExecutable doctor
    if ($LASTEXITCODE -ne 0) {
        throw "The packaged executable failed the doctor check."
    }
    $doctor = $doctorRaw | ConvertFrom-Json
    if (-not $doctor.samples_available) {
        throw "The packaged executable is missing bundled samples."
    }
    if (-not $doctor.runtime.openslide_available) {
        throw "The packaged executable could not load the OpenSlide runtime."
    }

    & $resolvedExecutable init --workspace $runtimeDir | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "The packaged executable failed to initialize a workspace."
    }

    & $resolvedExecutable demo --workspace $runtimeDir | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "The packaged executable failed to seed demo data."
    }

    $reportRaw = & $resolvedExecutable report --workspace $runtimeDir
    if ($LASTEXITCODE -ne 0) {
        throw "The packaged executable failed to report workspace state."
    }
    $report = $reportRaw | ConvertFrom-Json
    if ([int]$report.summary.total -lt 3) {
        throw "The packaged executable smoke test expected at least three demo jobs."
    }

    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
    $listener.Start()
    $servePort = $listener.LocalEndpoint.Port
    $listener.Stop()
    $existingProcessIds = @(
        Get-Process PathFlowGuard -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty Id
    )
    $serveArguments = @(
        "serve"
        "--workspace"
        ('"{0}"' -f $runtimeDir)
        "--host"
        "127.0.0.1"
        "--port"
        "$servePort"
    ) -join " "
    $serverProcess = Start-Process `
        -FilePath $resolvedExecutable `
        -ArgumentList $serveArguments `
        -PassThru
    try {
        $deadline = (Get-Date).AddSeconds(20)
        $healthy = $false
        while ((Get-Date) -lt $deadline) {
            try {
                $health = Invoke-RestMethod -Uri "http://127.0.0.1:$servePort/healthz" -TimeoutSec 2
                if ($health.status -eq "ok") {
                    $healthy = $true
                    break
                }
            }
            catch {
                Start-Sleep -Milliseconds 500
            }
        }

        if (-not $healthy) {
            throw "The packaged executable failed to start the dashboard and API server."
        }
    }
    finally {
        $spawnedProcesses = @(
            Get-Process PathFlowGuard -ErrorAction SilentlyContinue |
                Where-Object { $_.Id -notin $existingProcessIds }
        )
        foreach ($spawnedProcess in $spawnedProcesses) {
            Stop-Process -Id $spawnedProcess.Id -Force -ErrorAction SilentlyContinue
        }
        if ($null -ne $serverProcess -and -not $serverProcess.HasExited) {
            Stop-Process -Id $serverProcess.Id -Force
            $null = $serverProcess.WaitForExit()
        }
    }

    $extractRaw = & $resolvedExecutable extract ".\samples\packages\accept-package"
    if ($LASTEXITCODE -ne 0) {
        throw "The packaged executable failed to extract metrics from the sample package."
    }
    $extract = $extractRaw | ConvertFrom-Json
    if ([double]$extract.focus_score -le 0) {
        throw "The packaged executable returned an invalid focus score."
    }
}
finally {
    if (Test-Path -LiteralPath $runtimeDir) {
        Remove-Item -LiteralPath $runtimeDir -Recurse -Force
    }
}

Write-Host "Windows release smoke test passed."
