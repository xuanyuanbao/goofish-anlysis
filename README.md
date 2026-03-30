# 闲鱼教育资料趋势采集与报表系统

一个可直接运行的第一版实现，默认使用 `sqlite3 + fixture 采集器 + 标准库 CSV/XLSX 导出` 跑通整条链路。

## 快速开始

```bash
python main_daily.py --backfill-days 14
python main_weekly.py
python main_monthly.py
```

运行完成后会生成：

- `data/xianyu_report.db`
- `reports/daily/*.csv`
- `reports/daily/*.xlsx`
- `reports/weekly/*.csv`
- `reports/weekly/*.xlsx`
- `reports/monthly/*.csv`
- `reports/monthly/*.xlsx`

## 采集模式

默认：

- `XY_CRAWLER_MODE=fixture`

可选：

- `XY_CRAWLER_MODE=xianyu_http`
- `XY_CRAWLER_MODE=xianyu_auto`

说明：

- `fixture`：本地零依赖，可直接跑通整条链路。
- `xianyu_http`：走闲鱼真实搜索接口 `mtop.taobao.idlemtopsearch.pc.search`。
- `xianyu_auto`：优先走真实接口，失败时自动回退到 fixture，适合本地联调。

## 真实闲鱼采集配置

建议至少提供你自己浏览器里的 Cookie：

```bash
set XY_CRAWLER_MODE=xianyu_http
set XY_XIANYU_COOKIE_STRING=_m_h5_tk=...; _m_h5_tk_enc=...; cna=...; xlly_s=...
python main_daily.py --limit 20
```

支持的关键环境变量：

- `XY_XIANYU_COOKIE_STRING`
- `XY_XIANYU_API_BASE`，默认 `https://h5api.m.goofish.com/h5`
- `XY_XIANYU_APP_KEY`，默认 `34839810`
- `XY_XIANYU_ROWS_PER_PAGE`，默认 `30`
- `XY_XIANYU_TIMEOUT_SECONDS`，默认 `20`
- `XY_XIANYU_RETRY_COUNT`，默认 `2`
- `XY_XIANYU_REQUEST_DELAY_SECONDS`，默认 `0.8`

## 定时任务

程序层已经支持分时调度：

- `python main_daily.py --mode crawl`
- `python main_daily.py --mode report`
- `python main_weekly.py`
- `python main_monthly.py`

仓库里已经补好了两类调度文件：

- Linux cron 示例：[cron_example.txt](/D:/develop/python_develop/simple-project/goofish-anlysis/scheduler/cron_example.txt)
- Windows 定时任务注册脚本：[register_windows_tasks.ps1](/D:/develop/python_develop/simple-project/goofish-anlysis/scheduler/register_windows_tasks.ps1)

当前默认节奏是：

- 每天 `09:00` 抓取
- 每天 `13:00` 抓取
- 每天 `19:00` 抓取
- 每天 `23:00` 生成日报
- 每周一 `23:30` 生成周报
- 每月 `1` 日 `01:00` 生成月报

Windows 注册示例：

```powershell
powershell -ExecutionPolicy Bypass -File .\scheduler\register_windows_tasks.ps1 -Force
```

如果你要把真实 Cookie 一起写进任务：

```powershell
powershell -ExecutionPolicy Bypass -File .\scheduler\register_windows_tasks.ps1 `
  -CrawlerMode xianyu_http `
  -CookieString "_m_h5_tk=...; _m_h5_tk_enc=...; cna=..."
```

## 已知限制

- 闲鱼搜索接口有风控，纯 HTTP 请求可能触发 `RGV587_ERROR` 或“非法访问”。
- 如果触发风控，优先换新 Cookie、降低频率，或临时使用 `xianyu_auto` / `fixture`。
- 已提供 `db/mysql_init.sql`，后续可以切换到 MySQL 部署。
