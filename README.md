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

## 说明

- 默认 `XY_CRAWLER_MODE=fixture`，本地零依赖可直接运行。
- 已提供 `db/mysql_init.sql`，后续可切换到 MySQL 部署。
- `crawler/xianyu_http.py` 预留了真实闲鱼采集扩展点，确认目标接口后可继续接入。
