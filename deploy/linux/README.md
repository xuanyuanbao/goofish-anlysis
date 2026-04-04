# Linux 部署说明

这个目录用于把当前项目迁移到 Linux 服务器运行。当前推荐目标环境：

- Linux：Ubuntu / Debian / CentOS 任意一种
- Docker：用于运行应用镜像和 MySQL 容器
- Python：容器内运行，无需宿主机单独维护 Python 环境
- MySQL：运行在 Docker 容器中
- 采集模式：优先 `xianyu_curl`
- 统一启动程序：`python3 main.py`

## 目录文件用途与时效性

### 当前仍在使用的生产文件

- `Dockerfile`：应用镜像构建文件
- `build_image.sh`：带国内镜像源参数的 Docker 构建脚本
- `app.env.example`：应用环境变量模板
- `mysql.env.example`：MySQL 容器环境变量模板
- `docker-compose.mysql.yml`：MySQL 容器启动定义
- `mysql_bootstrap.sql`：建库、建表、建用户一体化 SQL
- `apply_mysql_bootstrap.sh`：把 bootstrap SQL 执行到 MySQL 容器
- `run_job.sh`：Linux 统一启动脚本
- `run_daily.sh` / `run_weekly.sh` / `run_monthly.sh`：旧入口兼容包装
- `install_cron.sh` / `uninstall_cron.sh`：安装和卸载 cron
- `check_mysql_ready.sh`：MySQL 就绪检查
- `healthcheck.sh`：应用健康检查
- `backup_mysql.sh`：MySQL 逻辑备份
- `backup_artifacts.sh`：报表与日志归档备份

### 仅用于本地演示或辅助排障

- `run_smoke.sh`：本地或部署后做 fixture 冒烟验证
- `cron_example.txt`：作为阅读示例，实际推荐直接使用 `install_cron.sh`

### 不应提交的运行态文件

以下内容是运行态文件，不纳入仓库源码主线：

- `app.env`
- `mysql.env`
- `mysql-data/`

这些已经被仓库根目录的 `.gitignore` 排除。

## 1. 安装 Docker

```bash
bash deploy/linux/install_docker.sh
```

如果服务器拉取基础镜像很慢，仓库默认已经做了构建加速：

- Python 基础镜像默认走 `m.daocloud.io/docker.io/library/python:3.12-slim`
- MySQL 镜像默认走 `m.daocloud.io/docker.io/library/mysql:8.4`
- `apt` 默认走清华 Debian 镜像
- `pip` 默认走清华 PyPI 镜像

## 2. 启动 MySQL 容器

```bash
cp deploy/linux/mysql.env.example deploy/linux/mysql.env
bash deploy/linux/install_mysql_docker.sh
```

如果你已经有独立 MySQL 服务，也可以跳过这一步，直接把应用连接到现有数据库。

## 3. 初始化数据库

如果 MySQL 容器已经启动，但还没有业务库、业务用户和表结构，执行：

```bash
bash deploy/linux/apply_mysql_bootstrap.sh
```

默认会创建：

- database: `xianyu_report`
- user: `xianyu`
- password: `xianyu123456`

如果你要自定义账号密码，请同步修改：

- `deploy/linux/mysql_bootstrap.sql`
- `deploy/linux/app.env`

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

- 宿主机直接运行应用时，`XY_MYSQL_HOST` 通常填 `127.0.0.1`
- 应用也运行在 Docker 容器里时，`XY_MYSQL_HOST` 通常填 MySQL 容器名，例如 `xianyu-mysql`

## 5. 构建应用镜像

在仓库根目录执行：

```bash
bash deploy/linux/build_image.sh
```

如果你要手工覆盖镜像源，可用：

```bash
BASE_IMAGE=m.daocloud.io/docker.io/library/python:3.12-slim \
APT_MIRROR=https://mirrors.tuna.tsinghua.edu.cn \
PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn \
bash deploy/linux/build_image.sh
```

## 6. 统一运行方式

推荐优先用统一入口：

```bash
bash deploy/linux/run_job.sh daily --mode full --date 2026-03-31
bash deploy/linux/run_job.sh weekly --date 2026-03-31
bash deploy/linux/run_job.sh monthly --month 2026-03
```

对应 Docker 直接运行示例：

```bash
docker run --rm \
  --env-file deploy/linux/app.env \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/reports:/app/reports" \
  -v "$(pwd)/logs:/app/logs" \
  goofish-analysis:latest \
  daily --mode full --date 2026-03-31
```

## 7. cron 定时任务

统一安装：

```bash
bash deploy/linux/install_cron.sh
```

统一卸载：

```bash
bash deploy/linux/uninstall_cron.sh
```

当前默认节奏：

- 每天 `09:00`、`13:00`、`19:00` 抓取
- 每天 `23:00` 生成日报
- 每周一 `23:30` 生成周报
- 每月 `1` 日 `01:00` 生成月报

说明：

- Linux 生产调度以这里为准
- 仓库中的 `scheduler/` 目录是 Windows 开发机兼容脚本，不是 Linux 生产调度主链路

## 8. 部署后验收

建议按这个顺序验收：

1. `docker ps` 能看到 MySQL 容器处于运行状态
2. `bash deploy/linux/apply_mysql_bootstrap.sh` 成功
3. `bash deploy/linux/check_mysql_ready.sh` 成功
4. `bash deploy/linux/build_image.sh` 成功
5. `app.env` 中确认 `XY_DB_BACKEND=mysql`
6. `app.env` 中填入真实 `XY_XIANYU_COOKIE_STRING`
7. 执行 `bash deploy/linux/run_job.sh daily --mode crawl --limit 5`
8. 检查 `logs/daily.log`、`logs/error.log`、`logs/alert.log`
9. 检查 MySQL 中 `item_snapshot` 是否有新增数据
10. 执行 `bash deploy/linux/run_job.sh daily --mode report`
11. 检查 `reports/daily/` 是否生成 CSV / XLSX
12. 执行 `bash deploy/linux/healthcheck.sh`

推荐验收 SQL：

```sql
SELECT COUNT(*) FROM item_snapshot;

SELECT COUNT(*) FROM job_run_history;

SELECT COUNT(*) FROM keyword_failure_log;

SELECT COUNT(*) FROM data_quality_issue;
```

## 9. 运维脚本

当前仓库已经提供这几类运维脚本：

- 就绪检查：`check_mysql_ready.sh`
- 健康检查：`healthcheck.sh`
- 数据库备份：`backup_mysql.sh`
- 报表与日志归档：`backup_artifacts.sh`

建议在正式环境中结合 cron 再补一层备份任务。

## 10. 关于 `xianyu_curl`

`xianyu_curl` 是当前最适合 Linux 小机器运行的真实采集模式，优点是：

- 轻量
- 不依赖浏览器常驻
- 容器内运行简单
- 对 2C2G 机器更友好

当前限制仍然是：

- 依然会遇到闲鱼风控
- Cookie 过期后需要更新
- `desc_text` 深抓属于增强补全，不是 100% 稳定字段

如果后续要继续增强，可以优先从 Cookie 更新机制、质量规则和详情页解析稳定性继续推进。


## 11. ?????????

?? Linux ????? `xianyu_curl` ? `xianyu_http` ???

- `FAIL_SYS_USER_VALIDATE`
- `RGV587_ERROR`
- `punish?action=captcha`

?????? IP ??????????????????????

1. ??? Windows / Chrome ??? `xianyu_browser`
2. ???????? Linux ?? MySQL
3. Linux ???????? `daily --mode report`?`weekly`?`monthly`

?????
- [deploy/local/README.md](/D:/develop/python_develop/simple-project/goofish-anlysis/deploy/local/README.md)
- [deploy/local/collector.env.example](/D:/develop/python_develop/simple-project/goofish-anlysis/deploy/local/collector.env.example)

???????????????? curl ??????????????????


## ????

???????? `Asia/Shanghai`?

- ????????????????????
- SQLite ????????????????????
- MySQL ??????? `time_zone = '+08:00'`
- Linux Docker ??????????? `TZ=Asia/Shanghai`
