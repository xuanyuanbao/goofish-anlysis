param(
    [switch]$InstallChrome = $true
)

$ErrorActionPreference = 'Stop'

py -m pip install playwright
if ($InstallChrome) {
    python -m playwright install chrome
}
