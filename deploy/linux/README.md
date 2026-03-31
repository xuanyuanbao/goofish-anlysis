# Linux 迁移说明

这个目录用于把当前项目迁移到 Linux 服务器运行，目标环境默认是：

- Linux: Ubuntu / Debian / CentOS 中任意一种
- Python: 3.11+
- MySQL: 运行在 Docker 容器中
- 采集模式: `xianyu_curl` 或 `xianyu_http`

## 1. 安装 Docker

在目标 Linux 服务器执行：

```bash
bash deploy/linux/install_docker.sh
```

脚本会：

- 安装 `curl`
- 使用官方安装脚本安装 Docker Engine
- 自动启动 Docker 服务

## 2. 启动 MySQL 容器

先复制 MySQL 环境变量模板：

```bash
cp deploy/linux/mysql.env.example deploy/linux/mysql.env
```

按需修改其中的密码和端口，然后执行：

```bash
bash deploy/linux/install_mysql_docker.sh
```

脚本会：

- 创建本地持久化目录 `deploy/linux/mysql-data/`
- 使用 `docker compose` 启动 MySQL 8 容器
- 自动挂载仓库里的 `db/mysql_init.sql`

默认数据库信息：

- host: `127.0.0.1`
- port: `3306`
- database: `xianyu_report`
- user: `xianyu`

## 3. 安装 Python 依赖

建议在 Linux 上单独创建虚拟环境：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 4. 准备应用环境变量

复制应用模板：

```bash
cp deploy/linux/app.env.example deploy/linux/app.env
```

重点检查这些配置：

- `XY_DB_BACKEND=mysql`
- `XY_MYSQL_HOST`
- `XY_MYSQL_PORT`
- `XY_MYSQL_USER`
- `XY_MYSQL_PASSWORD`
- `XY_MYSQL_DATABASE`
- `XY_CRAWLER_MODE=xianyu_curl`
- `XY_XIANYU_COOKIE_STRING`

说明：

- `xianyu_curl` 是这次新增的独立采集模式，适合 Linux 服务器直接运行
- 它依赖系统自带的 `curl`
- 如果闲鱼风控收紧，仍然需要你提供有效 Cookie

## 5. 手工运行

生成日采集和日报：

```bash
bash deploy/linux/run_daily.sh --mode full --date 2026-03-30
```

只跑采集：

```bash
bash deploy/linux/run_daily.sh --mode crawl --limit 20
```

生成周报：

```bash
bash deploy/linux/run_weekly.sh --date 2026-03-30
```

生成月报：

```bash
bash deploy/linux/run_monthly.sh --month 2026-03
```

## 6. Linux cron

参考模板：

```text
deploy/linux/cron_example.txt
```

一键安装：

```bash
bash deploy/linux/install_cron.sh
```

一键卸载：

```bash
bash deploy/linux/uninstall_cron.sh
```

默认建议节奏：

- 每天 `09:00`、`13:00`、`19:00` 抓取
- 每天 `23:00` 生成日报
- 每周一 `23:30` 生成周报
- 每月 `1` 日 `01:00` 生成月报

## 7. Linux 联调检查

先做 MySQL 就绪检查：

```bash
bash deploy/linux/check_mysql_ready.sh
```

建议按下面顺序验收：

1. `docker ps` 能看到 MySQL 容器处于运行状态
2. `bash deploy/linux/check_mysql_ready.sh` 返回成功
3. `source .venv/bin/activate && python3 -c "import pymysql"` 成功
4. `cp deploy/linux/app.env.example deploy/linux/app.env` 后，确认 `XY_DB_BACKEND=mysql`
5. 在 `app.env` 中填入真实 `XY_XIANYU_COOKIE_STRING`
6. 执行 `bash deploy/linux/run_daily.sh --mode crawl --limit 5`
7. 检查 `logs/daily.log` 和 `logs/error.log`
8. 检查 MySQL 中 `item_snapshot` 是否有新增数据
9. 执行 `bash deploy/linux/run_daily.sh --mode report`
10. 检查 `reports/daily/` 是否生成 CSV / XLSX

推荐验收 SQL：

```sql
SELECT COUNT(*) FROM item_snapshot;
SELECT snapshot_date, keyword, COUNT(*) AS item_count
FROM item_snapshot
GROUP BY snapshot_date, keyword
ORDER BY snapshot_date DESC, keyword ASC
LIMIT 20;
```

## 8. 关于 curl 采集模式

`xianyu_curl` 这套模式是可以放到 Linux 上独立运行的。

它的优点是：

- 比浏览器自动化更轻
- 对 2 核 2G 机器更友好
- 部署简单，只依赖系统 `curl`

它的限制是：

- 依然会遇到闲鱼风控
- Cookie 过期后需要更新
- `desc_text` 深抓是“尽力补全”，不是 100% 稳定字段

如果后续你要进一步增强稳定性，可以继续往下做两件事：

1. 加入更稳定的详情页结构化解析
2. 增加登录态 Cookie 的自动刷新方式
