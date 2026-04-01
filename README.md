# 闲鱼教育资料趋势采集与报表系统

这是一个面向 Linux 服务器部署的一期实现，当前已经具备以下能力：

- 关键词配置读取与初始化种子词导入
- 闲鱼搜索结果采集与商品快照入库
- `fixture / xianyu_http / xianyu_curl / xianyu_auto` 四种采集模式
- 日报、周报、月报统计与 CSV / XLSX 导出
- SQLite / MySQL 双后端
- Linux Docker / MySQL / cron 部署脚本
- 关键词级失败隔离、独立 `logs/error.log` 与 `logs/alert.log`
- 运行台账、数据质量记录、健康检查与备份脚本
- 统一启动程序 `main.py`

## 当前阶段

当前项目已经从“技术方案设计”进入“Linux 试运行与稳定化”阶段。

核心闭环已经打通：

1. 关键词读取
2. 搜索采集
3. 数据清洗
4. 快照入库
5. 日 / 周 / 月统计
6. 报表导出
7. Linux 定时运行

当前更关注的是采集稳定性、Cookie 有效性、详情页深抓质量和运维可观测性。

## 仓库文件时效性

### 当前主入口与核心代码

这些文件和目录是当前仍在主链路中使用的：

- [main.py](/D:/develop/python_develop/simple-project/goofish-anlysis/main.py)
- [pipeline.py](/D:/develop/python_develop/simple-project/goofish-anlysis/pipeline.py)
- [models.py](/D:/develop/python_develop/simple-project/goofish-anlysis/models.py)
- [config/settings.py](/D:/develop/python_develop/simple-project/goofish-anlysis/config/settings.py)
- [analyzer](/D:/develop/python_develop/simple-project/goofish-anlysis/analyzer)
- [crawler](/D:/develop/python_develop/simple-project/goofish-anlysis/crawler)
- [db](/D:/develop/python_develop/simple-project/goofish-anlysis/db)
- [exporter](/D:/develop/python_develop/simple-project/goofish-anlysis/exporter)
- [utils](/D:/develop/python_develop/simple-project/goofish-anlysis/utils)
- [fixtures/keywords.csv](/D:/develop/python_develop/simple-project/goofish-anlysis/fixtures/keywords.csv)

### 兼容入口

以下文件仍可运行，但已经不是推荐主入口，保留它们主要是为了兼容旧命令和历史脚本：

- [main_daily.py](/D:/develop/python_develop/simple-project/goofish-anlysis/main_daily.py)
- [main_weekly.py](/D:/develop/python_develop/simple-project/goofish-anlysis/main_weekly.py)
- [main_monthly.py](/D:/develop/python_develop/simple-project/goofish-anlysis/main_monthly.py)

推荐优先使用：

```bash
python main.py daily
python main.py weekly
python main.py monthly
```

### Linux 生产部署文件

以下目录和文件是 Linux 生产部署主链路：

- [deploy/linux/README.md](/D:/develop/python_develop/simple-project/goofish-anlysis/deploy/linux/README.md)
- [deploy/linux/OPERATIONS.md](/D:/develop/python_develop/simple-project/goofish-anlysis/deploy/linux/OPERATIONS.md)
- [deploy/linux/Dockerfile](/D:/develop/python_develop/simple-project/goofish-anlysis/deploy/linux/Dockerfile)
- [deploy/linux/build_image.sh](/D:/develop/python_develop/simple-project/goofish-anlysis/deploy/linux/build_image.sh)
- [deploy/linux/run_job.sh](/D:/develop/python_develop/simple-project/goofish-anlysis/deploy/linux/run_job.sh)
- [deploy/linux/install_cron.sh](/D:/develop/python_develop/simple-project/goofish-anlysis/deploy/linux/install_cron.sh)
- [deploy/linux/check_mysql_ready.sh](/D:/develop/python_develop/simple-project/goofish-anlysis/deploy/linux/check_mysql_ready.sh)
- [deploy/linux/healthcheck.sh](/D:/develop/python_develop/simple-project/goofish-anlysis/deploy/linux/healthcheck.sh)
- [deploy/linux/backup_mysql.sh](/D:/develop/python_develop/simple-project/goofish-anlysis/deploy/linux/backup_mysql.sh)
- [deploy/linux/backup_artifacts.sh](/D:/develop/python_develop/simple-project/goofish-anlysis/deploy/linux/backup_artifacts.sh)

### 开发机兼容文件

以下目录主要服务于 Windows 开发机，不属于 Linux 生产主链路：

- [scheduler](/D:/develop/python_develop/simple-project/goofish-anlysis/scheduler)

它们仍然有用，但不需要带入 Linux 生产调度思路。

### 运行时文件

以下内容属于运行产物，不应作为源码主线维护：

- `data/`
- `logs/`
- `reports/`
- `deploy/linux/app.env`
- `deploy/linux/mysql.env`
- `deploy/linux/mysql-data/`
- `.idea/`
- `__pycache__/`

这些内容已经通过 [.gitignore](/D:/develop/python_develop/simple-project/goofish-anlysis/.gitignore) 排除。

例外是演示产物：

- [demo/generated](/D:/develop/python_develop/simple-project/goofish-anlysis/demo/generated)

这部分是刻意保留的固定 demo，用于本地演示和验收。

## 快速开始

本地最小可运行方式：

```bash
python main.py daily --backfill-days 14
python main.py weekly
python main.py monthly
```

默认会生成：

- `data/xianyu_report.db`
- `reports/daily/*.csv`
- `reports/daily/*.xlsx`
- `reports/weekly/*.csv`
- `reports/weekly/*.xlsx`
- `reports/monthly/*.csv`
- `reports/monthly/*.xlsx`
- `logs/daily.log`
- `logs/weekly.log`
- `logs/monthly.log`
- `logs/error.log`
- `logs/alert.log`

## 统一启动程序

统一入口是：

```bash
python main.py daily --mode full --date 2026-03-31
python main.py weekly --date 2026-03-31
python main.py monthly --month 2026-03
```

`daily` 子命令支持：

- `--mode full`
- `--mode crawl`
- `--mode report`
- `--backfill-days`
- `--limit`

## 数据库后端

默认：

```bash
XY_DB_BACKEND=sqlite
```

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

- [db/sqlite_init.sql](/D:/develop/python_develop/simple-project/goofish-anlysis/db/sqlite_init.sql)
- [db/mysql_init.sql](/D:/develop/python_develop/simple-project/goofish-anlysis/db/mysql_init.sql)
- [deploy/linux/mysql_bootstrap.sql](/D:/develop/python_develop/simple-project/goofish-anlysis/deploy/linux/mysql_bootstrap.sql)

当前除了业务表，还补充了运行与质量跟踪表：

- `job_run_history`
- `keyword_failure_log`
- `data_quality_issue`

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

详情页描述增强开关：

```bash
XY_XIANYU_FETCH_DETAIL_DESC=1
XY_XIANYU_DETAIL_MAX_ITEMS_PER_KEYWORD=5
XY_XIANYU_DETAIL_MIN_LENGTH=18
```

## 报表与可观测性

当前报表已经做了这些增强：

- XLSX 自动列宽
- 单元格自动换行
- 顶部冻结
- 自动筛选
- 汇总 Sheet
- 关键词机会榜与重点摘要

当前日志与运维侧已经具备：

- 任务日志：`logs/daily.log`、`logs/weekly.log`、`logs/monthly.log`
- 错误日志：`logs/error.log`
- 告警日志：`logs/alert.log`
- 运行台账：`job_run_history`
- 失败关键词记录：`keyword_failure_log`
- 数据质量记录：`data_quality_issue`

## Linux 部署

Linux 迁移和部署资料在：

- [deploy/linux/README.md](/D:/develop/python_develop/simple-project/goofish-anlysis/deploy/linux/README.md)
- [deploy/linux/OPERATIONS.md](/D:/develop/python_develop/simple-project/goofish-anlysis/deploy/linux/OPERATIONS.md)

典型流程：

```bash
bash deploy/linux/install_docker.sh
cp deploy/linux/mysql.env.example deploy/linux/mysql.env
bash deploy/linux/install_mysql_docker.sh
bash deploy/linux/apply_mysql_bootstrap.sh
cp deploy/linux/app.env.example deploy/linux/app.env
bash deploy/linux/build_image.sh
bash deploy/linux/install_cron.sh
```

构建提速已经做进仓库：

- Docker 基础镜像默认使用国内镜像前缀
- Dockerfile 里的 `apt` 默认切到清华镜像
- Dockerfile 里的 `pip` 默认切到清华 PyPI 镜像

## Demo 输出

为了方便先在 Windows 开发机看结果，再迁移到 Linux，本仓库额外保留了一套固定 demo：

- [demo/README.md](/D:/develop/python_develop/simple-project/goofish-anlysis/demo/README.md)
- [demo/generate_demo_bundle.py](/D:/develop/python_develop/simple-project/goofish-anlysis/demo/generate_demo_bundle.py)
- [demo/generated](/D:/develop/python_develop/simple-project/goofish-anlysis/demo/generated)

重新生成 demo：

```bash
python demo/generate_demo_bundle.py
```

## 当前已实现与仍需关注

已经落地的重点：

- SQLite / MySQL 双后端切换
- Linux Docker MySQL 一键启动脚本
- Linux cron 一键安装 / 卸载脚本
- MySQL 就绪检查、健康检查、备份脚本
- 建库、建表、建用户一体化 SQL
- 日报 / 周报 / 月报统一启动程序
- 关键词级失败隔离
- `error.log` 与 `alert.log`
- 运行台账与数据质量检查
- 独立 `xianyu_curl` 采集模式
- `crawler/parser.py` 深抓增强
- 固定 demo 报表与日志输出

仍建议继续增强的部分：

- 更稳定的真实 Cookie 管理与更新方式
- 更稳的详情页深度解析
- 更细的数据质量规则与自动告警
- 更丰富的报表摘要和经营建议

## 相关文档

- [xianyu_edu_material_trend_tech_plan.md](/D:/develop/python_develop/simple-project/goofish-anlysis/xianyu_edu_material_trend_tech_plan.md)
- [deploy/linux/README.md](/D:/develop/python_develop/simple-project/goofish-anlysis/deploy/linux/README.md)
- [deploy/linux/OPERATIONS.md](/D:/develop/python_develop/simple-project/goofish-anlysis/deploy/linux/OPERATIONS.md)
