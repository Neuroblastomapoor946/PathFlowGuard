param(
    [string]$Python = "",
    [switch]$SmokeTest
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
Set-Location $PSScriptRoot

if (-not $Python) {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $pythonArgs = @("py", "-3.12")
    }
    elseif (Get-Command python -ErrorAction SilentlyContinue) {
        $pythonArgs = @("python")
    }
    else {
        throw "No usable Python launcher was found. Install Python 3.12 or pass -Python explicitly."
    }
}
elseif ($Python -eq "py -3.12") {
    $pythonArgs = @("py", "-3.12")
}
elseif ($Python -match '^py\s+-') {
    $pythonArgs = @($Python -split '\s+')
}
else {
    $pythonArgs = @($Python)
}

& $pythonArgs[0] @($pythonArgs | Select-Object -Skip 1) -m pip install --upgrade pip
& $pythonArgs[0] @($pythonArgs | Select-Object -Skip 1) -m pip install --upgrade '.[dev]'
& $pythonArgs[0] @($pythonArgs | Select-Object -Skip 1) -m PyInstaller --noconfirm --clean PathFlowGuard.spec

if ($SmokeTest) {
    & "$PSScriptRoot\smoke_windows_release.ps1"
}

Write-Host ""
Write-Host "Build complete:"
Write-Host "  $PSScriptRoot\\dist\\PathFlowGuard.exe"
