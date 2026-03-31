# Linux 运行与运维补充说明

本文件补充说明当前 Linux 版部署完成后新增的生产化能力，重点包括：

- 采集运行台账
- 失败关键词记录
- 数据质量问题记录
- Excel 报表可读性优化
- 健康检查脚本
- 备份脚本

## 1. 运行台账

现在每次执行以下任务时，都会向数据库写入一条运行记录：

- `daily`
- `weekly`
- `monthly`

对应表：

- `job_run_history`
- `keyword_failure_log`
- `data_quality_issue`

你可以直接在 MySQL 里查看：

```sql
SELECT
  run_id,
  job_name,
  run_mode,
  run_status,
  target_label,
  keyword_total,
  keyword_success,
  keyword_failed,
  inserted_snapshots,
  daily_stats,
  item_scores,
  alert_level,
  finished_at
FROM job_run_history
ORDER BY finished_at DESC
LIMIT 20;
```

查看失败关键词：

```sql
SELECT
  run_id,
  keyword,
  category,
  error_type,
  error_message,
  created_at
FROM keyword_failure_log
ORDER BY id DESC
LIMIT 50;
```

查看数据质量问题：

```sql
SELECT
  run_id,
  keyword,
  item_id,
  issue_type,
  severity,
  issue_message,
  created_at
FROM data_quality_issue
ORDER BY id DESC
LIMIT 100;
```

## 2. 告警日志

新增文件：

- `logs/alert.log`

会记录这些情况：

- 全量关键词采集失败
- 抓取成功但没有写入快照
- 有关键词抓取失败
- 发现缺失或异常链接
- 描述字段过短比例偏高

## 3. Excel 报表优化

当前 XLSX 已经做了这些处理：

- 首行冻结
- 自动筛选
- 列宽按内容自动估算
- 长文本自动换行
- 表头加粗并加底色

对于日报：

- `daily_keyword_report_YYYY-MM-DD.xlsx` 新增 `summary`、`keyword_opportunity`
- `daily_item_report_YYYY-MM-DD.xlsx` 新增 `summary`
- `item_score` 工作表中补充了 `category`、`seller_name`、`desc_text`

## 4. 健康检查

执行：

```bash
bash deploy/linux/healthcheck.sh
```

会检查：

- Docker 是否可用
- 应用镜像是否存在
- MySQL 容器与表结构是否就绪
- 应用账号是否能连库
- 最近一次任务是否成功
- 应用容器入口是否可正常启动

## 5. 备份

### 5.1 备份 MySQL

```bash
bash deploy/linux/backup_mysql.sh
```

产物默认在：

- `backup/mysql/`

### 5.2 备份报表和日志

```bash
bash deploy/linux/backup_artifacts.sh
```

产物默认在：

- `backup/runtime/`

## 6. 推荐运维动作

建议日常巡检顺序：

1. `bash deploy/linux/healthcheck.sh`
2. 查看 `logs/cron.log`
3. 查看 `logs/alert.log`
4. 查看 `job_run_history`
5. 抽查最新日报 XLSX

建议备份顺序：

1. `bash deploy/linux/backup_mysql.sh`
2. `bash deploy/linux/backup_artifacts.sh`

## 7. 一次性升级提示

本轮升级新增了三个业务支撑表：

- `job_run_history`
- `keyword_failure_log`
- `data_quality_issue`

如果是已运行中的 Linux 服务器，升级代码后记得重新执行一次：

```bash
bash deploy/linux/apply_mysql_bootstrap.sh
```

这样 MySQL 会把新表补齐。
