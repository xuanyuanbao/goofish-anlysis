param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("daily_crawl", "daily_report", "weekly_report", "monthly_report")]
    [string]$JobName,

    [Parameter(Mandatory = $true)]
    [string]$ProjectDir,

    [string]$PythonExe = "python",
    [string]$CrawlerMode = "xianyu_http",
    [string]$CookieString = ""
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $ProjectDir

$env:XY_CRAWLER_MODE = $CrawlerMode
if ($CookieString) {
    $env:XY_XIANYU_COOKIE_STRING = $CookieString
}

switch ($JobName) {
    "daily_crawl" {
        & $PythonExe "main_daily.py" "--mode" "crawl"
    }
    "daily_report" {
        & $PythonExe "main_daily.py" "--mode" "report"
    }
    "weekly_report" {
        & $PythonExe "main_weekly.py"
    }
    "monthly_report" {
        & $PythonExe "main_monthly.py"
    }
}
