# Linux 迁移说明

这个目录用于把当前项目迁移到 Linux 服务器运行，目标环境默认是：

- Linux: Ubuntu / Debian / CentOS 任意一种
- Python: 3.11+
- MySQL: 运行在 Docker 容器中
- 采集模式: `xianyu_curl` 或 `xianyu_http`
- 统一启动程序: `python3 main.py`

## 目录说明

- `Dockerfile`: 应用容器镜像构建文件
- `build_image.sh`: 带国内镜像源参数的 Docker 构建脚本
- `app.env.example`: 应用环境变量模板
- `mysql.env.example`: MySQL 容器环境变量模板
- `mysql_bootstrap.sql`: 建库、建表、建用户一体化 SQL
- `apply_mysql_bootstrap.sh`: 把 bootstrap SQL 执行到 MySQL 容器
- `run_job.sh`: Linux 统一启动脚本
- `run_daily.sh`: 兼容旧调用，内部转发到统一入口
- `run_weekly.sh`: 兼容旧调用，内部转发到统一入口
- `run_monthly.sh`: 兼容旧调用，内部转发到统一入口
- `install_cron.sh`: 一键安装 cron
- `uninstall_cron.sh`: 一键卸载 cron
- `check_mysql_ready.sh`: MySQL 就绪检查

## 1. 安装 Docker

```bash
bash deploy/linux/install_docker.sh
```

如果你的服务器拉取 Docker 基础镜像很慢，建议优先使用仓库里默认配置的国内镜像前缀：

- Python 基础镜像默认走 `m.daocloud.io/docker.io/library/python:3.12-slim`
- MySQL 镜像默认走 `m.daocloud.io/docker.io/library/mysql:8.4`

## 2. 启动 MySQL 容器

```bash
cp deploy/linux/mysql.env.example deploy/linux/mysql.env
bash deploy/linux/install_mysql_docker.sh
```

这一步会启动一个 MySQL 8 容器。默认参数见 `mysql.env.example`。
如果你有更稳定的企业镜像仓库，也可以只改 `MYSQL_IMAGE`。

## 3. 执行建库建表建用户 SQL

如果你已经启动好 MySQL 容器，但还没创建业务库、业务用户和表结构，可以直接执行：

```bash
bash deploy/linux/apply_mysql_bootstrap.sh
```

它会把 `deploy/linux/mysql_bootstrap.sql` 导入到 MySQL 容器里。

默认会创建：

- database: `xianyu_report`
- user: `xianyu`
- password: `xianyu123456`

如果你要自定义账号密码，请同时修改：

- `deploy/linux/mysql_bootstrap.sql`
- `deploy/linux/app.env`

也可以手工执行：

```bash
docker exec -i xianyu-mysql mysql -uroot -proot123456 < deploy/linux/mysql_bootstrap.sql
```

## 4. 准备应用环境变量

```bash
cp deploy/linux/app.env.example deploy/linux/app.env
```

重点检查：

- `XY_DB_BACKEND=mysql`
- `XY_MYSQL_HOST`
- `XY_MYSQL_PORT`
- `XY_MYSQL_USER`
- `XY_MYSQL_PASSWORD`
- `XY_MYSQL_DATABASE`
- `XY_CRAWLER_MODE=xianyu_curl`
- `XY_XIANYU_COOKIE_STRING`

说明：

- 如果应用直接跑在 Linux 宿主机上，`XY_MYSQL_HOST` 通常填 `127.0.0.1`
- 如果应用跑在 Docker 容器里，`XY_MYSQL_HOST` 应填 MySQL 容器名或服务名，例如 `xianyu-mysql`

## 5. 统一启动程序

现在日报、周报、月报都已经收口到同一个启动程序：

```bash
python3 main.py daily --mode full --date 2026-03-31
python3 main.py weekly --date 2026-03-31
python3 main.py monthly --month 2026-03
```

Linux 下也可以通过统一脚本运行：

```bash
bash deploy/linux/run_job.sh daily --mode full --date 2026-03-31
bash deploy/linux/run_job.sh weekly --date 2026-03-31
bash deploy/linux/run_job.sh monthly --month 2026-03
```

## 6. 构建 Docker 镜像

在仓库根目录执行：

```bash
bash deploy/linux/build_image.sh
```

这个脚本默认做了三层加速：

- 基础镜像走国内 Docker Hub 镜像前缀
- `apt` 走清华 Debian 镜像
- `pip` 走清华 PyPI 镜像

如果你要手工指定镜像源，也可以：

```bash
BASE_IMAGE=m.daocloud.io/docker.io/library/python:3.12-slim \
APT_MIRROR=https://mirrors.tuna.tsinghua.edu.cn \
PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn \
bash deploy/linux/build_image.sh
```

## 7. 用 Docker 运行应用

日报全量：

```bash
docker run --rm \
  --env-file deploy/linux/app.env \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/reports:/app/reports" \
  -v "$(pwd)/logs:/app/logs" \
  goofish-analysis:latest \
  daily --mode full --date 2026-03-31
```

只抓取：

```bash
docker run --rm \
  --env-file deploy/linux/app.env \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/reports:/app/reports" \
  -v "$(pwd)/logs:/app/logs" \
  goofish-analysis:latest \
  daily --mode crawl --limit 20
```

周报：

```bash
docker run --rm \
  --env-file deploy/linux/app.env \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/reports:/app/reports" \
  -v "$(pwd)/logs:/app/logs" \
  goofish-analysis:latest \
  weekly --date 2026-03-31
```

月报：

```bash
docker run --rm \
  --env-file deploy/linux/app.env \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/reports:/app/reports" \
  -v "$(pwd)/logs:/app/logs" \
  goofish-analysis:latest \
  monthly --month 2026-03
```

## 8. Linux cron

统一安装：

```bash
bash deploy/linux/install_cron.sh
```

统一卸载：

```bash
bash deploy/linux/uninstall_cron.sh
```

默认节奏：

- 每天 `09:00`、`13:00`、`19:00` 抓取
- 每天 `23:00` 生成日报
- 每周一 `23:30` 生成周报
- 每月 `1` 日 `01:00` 生成月报

## 9. Linux 联调检查

先做 MySQL 就绪检查：

```bash
bash deploy/linux/check_mysql_ready.sh
```

建议按这个顺序验收：

1. `docker ps` 能看到 MySQL 容器处于运行状态
2. `bash deploy/linux/apply_mysql_bootstrap.sh` 成功
3. `bash deploy/linux/check_mysql_ready.sh` 成功
4. `app.env` 中确认 `XY_DB_BACKEND=mysql`
5. `app.env` 中填入真实 `XY_XIANYU_COOKIE_STRING`
6. 执行 `bash deploy/linux/run_job.sh daily --mode crawl --limit 5`
7. 检查 `logs/daily.log` 和 `logs/error.log`
8. 检查 MySQL 中 `item_snapshot` 是否有新增数据
9. 执行 `bash deploy/linux/run_job.sh daily --mode report`
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

## 10. 关于 curl 采集模式

`xianyu_curl` 可以放到 Linux 上独立运行，优点是轻量、对小机器更友好、容器部署简单。

当前限制仍然是：

- 依然会遇到闲鱼风控
- Cookie 过期后需要更新
- `desc_text` 深抓已经增强，但仍属于尽力补全，不是 100% 稳定字段
