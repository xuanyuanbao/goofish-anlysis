# Local Collector Mode

This directory is for the recommended split deployment:

- local Windows or desktop Chrome: run `xianyu_browser` to collect real snapshots
- Linux server: keep MySQL, daily report, weekly report, and monthly report jobs

## 1. Prepare the local collector environment

Copy the example file and fill in the remote MySQL settings:

```powershell
Copy-Item deploy/local/collector.env.example deploy/local/collector.env
```

Recommended values:

- `XY_DB_BACKEND=mysql`
- `XY_MYSQL_HOST=<your linux server ip>`
- `XY_CRAWLER_MODE=xianyu_browser`
- `XY_XIANYU_BROWSER_HEADLESS=0`
- `XY_XIANYU_BROWSER_CHANNEL=chrome`
- `XY_XIANYU_BROWSER_USER_DATA_DIR=data/browser_profile`

## 2. Install the optional browser dependency

```powershell
powershell -ExecutionPolicy Bypass -File deploy/local/install_browser_runtime.ps1
```

Or run the two commands manually:

```powershell
py -m pip install playwright
python -m playwright install chrome
```

## 3. Run a local crawl into the remote MySQL database

```powershell
Get-Content deploy/local/collector.env | ForEach-Object {
  if ($_ -match '^(?!#)([^=]+)=(.*)$') {
    [Environment]::SetEnvironmentVariable($matches[1], $matches[2], 'Process')
  }
}
python main.py daily --mode crawl --date 2026-04-01 --limit 20
```

On the first run, the browser window stays open for `XY_XIANYU_BROWSER_MANUAL_WAIT_SECONDS` so you can finish login or slider verification.

## 4. Keep the Linux server focused on reports

On Linux, keep using:

```bash
bash deploy/linux/run_job.sh daily --mode report
bash deploy/linux/run_job.sh weekly
bash deploy/linux/run_job.sh monthly
```


## 5. Optional: warm up the browser session first

If you prefer to log in first and run the collector second, use:

```powershell
python tools/open_xianyu_browser.py --wait-seconds 120
```

This is useful when you want to finish login or slider verification in a dedicated browser window, save the browser state, and then start `main.py daily --mode crawl` afterward.
