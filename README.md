# 闲鱼教育资料趋势采集与报表系统

这是一个面向 Linux 服务器部署的一期实现，当前已经具备：

- 关键词配置读取
- 搜索结果采集
- 商品快照入库
- 日 / 周 / 月统计
- Excel / CSV 报表导出
- SQLite / MySQL 双后端
- Linux Docker MySQL 部署脚本
- `fixture / xianyu_http / xianyu_curl / xianyu_auto` 四种采集模式
- 关键词级失败隔离与独立 `error.log`

## 快速开始

本地最小可运行方式：

```bash
python main_daily.py --backfill-days 14
python main_weekly.py
python main_monthly.py
```

默认会生成：

- `data/xianyu_report.db`
- `reports/daily/*.csv`
- `reports/daily/*.xlsx`
- `reports/weekly/*.csv`
- `reports/weekly/*.xlsx`
- `reports/monthly/*.csv`
- `reports/monthly/*.xlsx`
- `logs/error.log`

## 数据库后端

默认：

- `XY_DB_BACKEND=sqlite`

切到 MySQL：

```bash
XY_DB_BACKEND=mysql
XY_MYSQL_HOST=127.0.0.1
XY_MYSQL_PORT=3306
XY_MYSQL_USER=xianyu
XY_MYSQL_PASSWORD=xianyu123456
XY_MYSQL_DATABASE=xianyu_report
```

对应表结构：

- `db/sqlite_init.sql`
- `db/mysql_init.sql`

## 采集模式

支持四种模式：

- `XY_CRAWLER_MODE=fixture`
- `XY_CRAWLER_MODE=xianyu_http`
- `XY_CRAWLER_MODE=xianyu_curl`
- `XY_CRAWLER_MODE=xianyu_auto`

说明：

- `fixture`：本地零依赖演示模式，最稳定
- `xianyu_http`：直接用 Python HTTP 请求真实接口
- `xianyu_curl`：独立的 Linux 友好模式，调用系统 `curl`
- `xianyu_auto`：优先 `xianyu_curl`，再尝试 `xianyu_http`，失败后回退到 `fixture`

真实采集至少建议提供：

```bash
XY_XIANYU_COOKIE_STRING=_m_h5_tk=...; _m_h5_tk_enc=...; cna=...
```

详情摘要增强开关：

```bash
XY_XIANYU_FETCH_DETAIL_DESC=1
XY_XIANYU_DETAIL_MAX_ITEMS_PER_KEYWORD=5
XY_XIANYU_DETAIL_MIN_LENGTH=18
```

## Linux 部署

Linux 迁移资料在：

- `deploy/linux/README.md`
- `deploy/linux/install_docker.sh`
- `deploy/linux/install_mysql_docker.sh`
- `deploy/linux/install_cron.sh`
- `deploy/linux/uninstall_cron.sh`
- `deploy/linux/check_mysql_ready.sh`
- `deploy/linux/docker-compose.mysql.yml`
- `deploy/linux/mysql.env.example`
- `deploy/linux/app.env.example`
- `deploy/linux/cron_example.txt`

典型流程：

```bash
bash deploy/linux/install_docker.sh
cp deploy/linux/mysql.env.example deploy/linux/mysql.env
bash deploy/linux/install_mysql_docker.sh
cp deploy/linux/app.env.example deploy/linux/app.env
bash deploy/linux/check_mysql_ready.sh
bash deploy/linux/install_cron.sh
```

## Demo 输出

为了方便先在 Windows 开发机看结果，再迁移到 Linux，本仓库额外保留了一套固定 demo：

- `demo/README.md`
- `demo/generate_demo_bundle.py`
- `demo/generated/`

重新生成 demo：

```bash
python demo/generate_demo_bundle.py
```

## 已实现与待继续增强

已经补上的重点：

- SQLite / MySQL 双后端切换
- Linux Docker MySQL 一键启动脚本
- Linux cron 一键安装 / 卸载脚本
- MySQL 就绪检查脚本
- 关键词级失败隔离
- 独立 `error.log`
- 独立 `xianyu_curl` 采集模式
- 解析逻辑拆分到 `crawler/parser.py`
- `desc_text` 搜索摘要 + 详情页补充
- 固定 demo 报表与日志输出

仍建议继续增强的部分：

- 更稳定的详情页深度解析
- 更稳的 Cookie 管理与更新方式
- Linux 真机上的 MySQL 联调与定时任务落地
