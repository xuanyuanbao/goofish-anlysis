# 闲鱼教育资料趋势采集与报表系统技术方案与实施对照（第一版）

## 1. 文档目的

这份文档既保留第一版技术方案，也同步当前仓库的实际实现状态，避免“方案写的是一版，仓库跑的是另一版”。

当前时间点：

- 代码阶段：第一版闭环已完成，进入 Linux 试运行和稳定化阶段
- 生产形态：Linux + Docker + MySQL + cron
- 主入口：`main.py`

## 2. 项目目标

面向闲鱼平台教育资料类虚拟商品，建设一个轻量级的数据采集与趋势分析系统，用于：

- 观察不同资料关键词的热度变化
- 识别上升或下降的赛道
- 观察价格区间与竞争强度
- 发现值得关注的关键词和商品
- 输出日报、周报、月报作为运营情报材料

系统设计优先满足：

- 轻量
- 可落地
- 可在 2 核 2G Linux 服务器运行

## 3. 第一版范围

### 已纳入范围

- 关键词配置管理
- 搜索结果采集
- 商品基础信息入库
- 每日商品快照存储
- 每日 / 每周 / 每月统计
- Excel / CSV 报表导出
- 日志输出
- cron 定时运行
- Linux Docker 部署
- MySQL 初始化与运维脚本
- 失败隔离、运行台账、数据质量记录

### 暂不纳入范围

- Web 前端
- REST API 服务
- Redis / MQ / ES
- 大规模高并发采集
- 多机部署
- 图片下载归档
- 复杂反爬绕过体系
- 官方销量精确获取

## 4. 当前实现阶段判断

当前项目已经不是“方案起草阶段”，而是“一期 MVP 已完成，并进入稳定化阶段”。

已完成的主链路：

1. 关键词读取
2. 搜索采集
3. 数据清洗
4. 商品快照入库
5. 日 / 周 / 月统计
6. CSV / XLSX 报表导出
7. Linux Docker 部署
8. cron 定时任务

当前重点从“补主功能”转向：

- 采集稳定性
- 真实 Cookie 管理
- 详情页深抓质量
- 运维可观测性
- 报表可读性与经营摘要

## 5. 总体架构

```text
Linux cron
    ↓
main.py
    ↓
pipeline.py
    ├── crawler/
    ├── analyzer/
    ├── db/
    └── exporter/
    ↓
MySQL / SQLite
    ↓
reports/ + logs/
```

说明：

- Linux 生产主入口已经统一到 `main.py`
- `main_daily.py`、`main_weekly.py`、`main_monthly.py` 仍保留，但属于兼容层
- Linux 生产调度已经切换到 `deploy/linux/` 目录，不再依赖 Windows `scheduler/`

## 6. 技术选型与实际实现

### 当前实际使用

- Python 3
- SQLite / MySQL 双后端
- Docker
- Linux cron
- 自定义 XLSX 导出器
- `curl` / HTTP 采集
- logging

### 当前采集模式

- `fixture`
- `xianyu_http`
- `xianyu_curl`
- `xianyu_auto`

推荐 Linux 生产优先使用：

- `xianyu_curl`

原因：

- 更轻量
- 对 2C2G 机器更友好
- 容器部署更简单

## 7. 模块设计与当前落地情况

### 7.1 关键词配置模块

目标：

- 维护关键词、分类、优先级、启停状态

当前实现：

- 已落表
- 已支持种子词初始化
- 当前主要通过数据库和初始化 CSV 维护

对应文件：

- `db/`
- `fixtures/keywords.csv`

### 7.2 数据采集模块

目标：

- 按关键词抓取搜索结果
- 解析商品标题、价格、链接、卖家、摘要
- 尽量补抓详情描述

当前实现：

- 已支持真实采集
- 已支持 `curl` 独立模式
- 已增加真实商品链接提取修复
- 已增加详情描述增强抓取

当前限制：

- 依赖 Cookie
- 会受到闲鱼风控
- `desc_text` 仍属于增强补全，不是稳定字段

对应文件：

- `crawler/crawl_keywords.py`
- `crawler/xianyu_curl.py`
- `crawler/xianyu_http.py`
- `crawler/parser.py`

### 7.3 数据清洗模块

目标：

- 清洗标题噪声
- 标准化价格与链接
- 去重与字段截断

当前实现：

- 已实现价格清洗
- 已实现 URL 规范化
- 已实现字段长度裁剪
- 已实现 seller / desc 等字段质量规则

对应文件：

- `analyzer/clean_data.py`

### 7.4 统计分析模块

目标：

- 计算每日热度、趋势、机会值
- 生成周报、月报聚合指标
- 支持商品评分

当前实现：

- 已具备 daily / weekly / monthly 统计
- 已支持机会分、趋势分
- 已支持商品评分

对应文件：

- `analyzer/calc_daily_stats.py`
- `analyzer/calc_weekly_stats.py`
- `analyzer/calc_monthly_stats.py`
- `analyzer/scoring.py`

### 7.5 数据质量与运行台账

这是当前比原始方案新增的一层能力。

新增目标：

- 记录每次运行是否成功
- 记录失败关键词
- 记录数据质量问题
- 为健康检查和后续告警提供依据

当前实现：

- 已落表
- 已在主流程写入
- 已支持 Linux 健康检查脚本读取

新增表：

- `job_run_history`
- `keyword_failure_log`
- `data_quality_issue`

对应文件：

- `models.py`
- `analyzer/data_quality.py`
- `db/base.py`
- `db/mysql_client.py`
- `db/sqlite_client.py`

### 7.6 报表导出模块

目标：

- 导出 CSV / XLSX
- 提供更适合直接打开查看的 Excel 报表

当前实现：

- 已支持 CSV / XLSX
- 已支持汇总 Sheet
- 已支持自动列宽
- 已支持自动换行
- 已支持冻结首行
- 已支持自动筛选

这部分已经从“能导出”升级到“打开就能看”。

对应文件：

- `exporter/export_csv.py`
- `exporter/export_excel.py`

## 8. 数据库设计

### 原始业务表

- `keyword_config`
- `item_snapshot`
- `keyword_daily_stats`
- `item_score_daily`

### 当前新增运维表

- `job_run_history`
- `keyword_failure_log`
- `data_quality_issue`

新增这些表的原因：

- 原始方案只覆盖业务数据，不足以支撑长期运维
- Linux 生产运行后，需要知道任务是否成功、哪些关键词失败、哪些数据字段质量有问题

## 9. 调度设计

### 当前 Linux 生产节奏

- 每天 `09:00` 抓取
- 每天 `13:00` 抓取
- 每天 `19:00` 抓取
- 每天 `23:00` 生成日报
- 每周一 `23:30` 生成周报
- 每月 `1` 日 `01:00` 生成月报

### 当前主链路

- Linux 使用 `deploy/linux/install_cron.sh`
- Windows `scheduler/` 仅保留为开发机兼容脚本

## 10. 仓库文件时效性结论

### 当前仍应保留并维护

- `main.py`
- `pipeline.py`
- `models.py`
- `config/`
- `crawler/`
- `analyzer/`
- `db/`
- `exporter/`
- `utils/`
- `deploy/linux/`
- `demo/`

### 当前可保留但已降级为兼容层

- `main_daily.py`
- `main_weekly.py`
- `main_monthly.py`

### 当前仅用于 Windows 开发机，不属于 Linux 生产主链路

- `scheduler/`

### 运行时文件不应纳入源码主线

- `data/`
- `logs/`
- `reports/`
- `.idea/`
- `__pycache__/`
- `deploy/linux/app.env`
- `deploy/linux/mysql.env`
- `deploy/linux/mysql-data/`

说明：

- 这些已经由 `.gitignore` 控制
- `demo/generated/` 是刻意保留的演示产物，不属于误提交

## 11. 运行与运维设计

当前仓库除业务功能外，已经补充以下运维能力：

- MySQL 初始化：`deploy/linux/mysql_bootstrap.sql`
- MySQL 就绪检查：`deploy/linux/check_mysql_ready.sh`
- 健康检查：`deploy/linux/healthcheck.sh`
- 数据库备份：`deploy/linux/backup_mysql.sh`
- 报表与日志备份：`deploy/linux/backup_artifacts.sh`
- Linux 部署说明：`deploy/linux/README.md`
- 运维说明：`deploy/linux/OPERATIONS.md`

这部分属于原始技术方案的增强项，但已经成为生产运行的必要组成部分。

## 12. 已完成项与剩余关注点

### 已完成项

- 统一主入口 `main.py`
- Linux Docker 化部署
- MySQL Docker 初始化
- `xianyu_curl` 独立模式
- 真实链接提取修复
- 关键词级失败隔离
- `error.log` 与 `alert.log`
- 运行台账
- 数据质量记录
- Excel 报表可读性优化
- 健康检查与备份脚本

### 剩余关注点

- Cookie 更新机制仍需要人工维护
- 详情页深抓仍可继续增强
- 真实采集仍可能受风控影响
- 数据质量规则还可以继续细化
- 报表中的经营摘要还可以继续增强

## 13. 下一阶段建议

下一阶段不建议再从“重新搭架构”开始，而应继续围绕稳定生产运行推进：

1. 继续增强 Cookie 管理与过期检查
2. 继续增强详情页深抓与 `desc_text` 质量
3. 细化数据质量规则与自动告警
4. 强化报表摘要和经营解释
5. 完善备份、恢复和回滚流程

## 14. 结论

这套方案当前已经从“第一版设计”演进为“第一版已落地，并进入稳定化”的状态。

因此后续维护原则建议固定为：

- 方案文档同步跟随仓库实际实现
- Linux 生产链路优先于 Windows 开发机脚本
- 主入口优先于兼容入口
- 运维可观测性与数据质量与业务功能同等重要
