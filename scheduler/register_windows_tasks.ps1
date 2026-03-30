param(
    [string]$PythonExe = "python",
    [string]$ProjectDir = (Split-Path -Parent $PSScriptRoot),
    [string]$CrawlerMode = "xianyu_http",
    [string]$CookieString = "",
    [string]$TaskPrefix = "GoofishAnalysis",
    [switch]$Force
)

$ErrorActionPreference = "Stop"

function New-TaskCommand {
    param(
        [string]$JobName,
        [string]$ProjectDir,
        [string]$PythonExe,
        [string]$CrawlerMode,
        [string]$CookieString
    )

    $runner = Join-Path $ProjectDir "scheduler\run_scheduled_job.ps1"
    $parts = @(
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", ('"{0}"' -f $runner),
        "-JobName", $JobName,
        "-ProjectDir", ('"{0}"' -f $ProjectDir),
        "-PythonExe", ('"{0}"' -f $PythonExe),
        "-CrawlerMode", $CrawlerMode
    )

    if ($CookieString) {
        $parts += @("-CookieString", ('"{0}"' -f $CookieString.Replace('"', '\"')))
    }

    return ($parts -join " ")
}

function Register-GoofishTask {
    param(
        [string]$TaskName,
        [string]$Schedule,
        [string]$StartTime,
        [string]$TaskRun,
        [string]$Days = ""
    )

    $arguments = @("/Create", "/TN", $TaskName, "/SC", $Schedule, "/ST", $StartTime, "/TR", $TaskRun)
    if ($Days) {
        $arguments += @("/D", $Days)
    }
    if ($Force) {
        $arguments += "/F"
    }

    & schtasks.exe @arguments
}

$taskRunDaily = New-TaskCommand -JobName "daily_crawl" -ProjectDir $ProjectDir -PythonExe $PythonExe -CrawlerMode $CrawlerMode -CookieString $CookieString
$taskRunReport = New-TaskCommand -JobName "daily_report" -ProjectDir $ProjectDir -PythonExe $PythonExe -CrawlerMode $CrawlerMode -CookieString $CookieString
$taskRunWeekly = New-TaskCommand -JobName "weekly_report" -ProjectDir $ProjectDir -PythonExe $PythonExe -CrawlerMode $CrawlerMode -CookieString $CookieString
$taskRunMonthly = New-TaskCommand -JobName "monthly_report" -ProjectDir $ProjectDir -PythonExe $PythonExe -CrawlerMode $CrawlerMode -CookieString $CookieString

Register-GoofishTask -TaskName "$TaskPrefix Daily Crawl 09" -Schedule "DAILY" -StartTime "09:00" -TaskRun $taskRunDaily
Register-GoofishTask -TaskName "$TaskPrefix Daily Crawl 13" -Schedule "DAILY" -StartTime "13:00" -TaskRun $taskRunDaily
Register-GoofishTask -TaskName "$TaskPrefix Daily Crawl 19" -Schedule "DAILY" -StartTime "19:00" -TaskRun $taskRunDaily
Register-GoofishTask -TaskName "$TaskPrefix Daily Report 23" -Schedule "DAILY" -StartTime "23:00" -TaskRun $taskRunReport
Register-GoofishTask -TaskName "$TaskPrefix Weekly Report" -Schedule "WEEKLY" -StartTime "23:30" -Days "MON" -TaskRun $taskRunWeekly
Register-GoofishTask -TaskName "$TaskPrefix Monthly Report" -Schedule "MONTHLY" -StartTime "01:00" -Days "1" -TaskRun $taskRunMonthly

Write-Output "Windows scheduled tasks registered."
Write-Output "Crawler mode: $CrawlerMode"
Write-Output "Project dir: $ProjectDir"
