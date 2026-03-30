# 闲鱼教育资料趋势采集与报表系统技术方案（第一版）

## 1. 项目背景

本项目面向闲鱼平台的教育资料类虚拟商品，目标是构建一个轻量级的数据采集与趋势分析系统，围绕以下方向开展：

- 小学、初中、高中资料
- 高考资料
- 大学课程资料
- 考研资料
- 考公资料
- 考编资料
- 教师资格证资料
- 其他教育考试类虚拟资料

第一版聚焦于：

1. 采集指定关键词下的商品数据
2. 建立每日商品快照
3. 统计关键词热度、价格分布、趋势变化
4. 生成日报、周报、月报
5. 不做前端页面，只输出 Excel / CSV 报表

系统优先满足“轻量、可落地、可在 2 核 2G 云服务器运行”的要求。

---

## 2. 项目目标

### 2.1 业务目标

构建“教育资料类虚拟商品趋势情报系统”，用于：

- 观察不同资料关键词的热度变化
- 识别近期上升或下降的赛道
- 观察价格区间与竞争强度
- 发现值得进入或加大投入的关键词
- 为自有资源池建设提供选品依据

### 2.2 技术目标

第一版系统应具备：

- 基于 Python 的定时采集能力
- 基于 MySQL 的数据存储能力
- 基于脚本的统计分析能力
- 基于 Excel / CSV 的报表导出能力
- 可通过 cron 定时触发运行

---

## 3. 第一版范围

### 3.1 包含内容

- 关键词配置管理（通过 MySQL 表维护）
- 搜索结果采集
- 商品基础信息入库
- 每日商品快照存储
- 每日统计计算
- 每周统计计算
- 每月统计计算
- Excel / CSV 报表导出
- 日志输出
- cron 定时运行

### 3.2 暂不包含内容

- Web 前端
- REST API 服务
- Redis
- 消息队列
- Elasticsearch
- 大规模高并发采集
- 多机部署
- 图片下载归档
- 复杂反爬绕过体系
- 真正的“官方销量”精确获取

---

## 4. 总体架构

第一版采用单机轻量架构：

```text
                   ┌────────────────────────────┐
                   │         Linux cron          │
                   │   定时触发 Python 脚本       │
                   └─────────────┬──────────────┘
                                 │
                                 ▼
                   ┌────────────────────────────┐
                   │        Python 主程序         │
                   │                            │
                   │ 1. 读取关键词配置            │
                   │ 2. 执行搜索采集              │
                   │ 3. 清洗解析数据              │
                   │ 4. 写入 MySQL               │
                   │ 5. 统计热度与趋势            │
                   │ 6. 导出 Excel/CSV 报表      │
                   └───────┬────────────┬───────┘
                           │            │
                           │写入        │导出
                           ▼            ▼
                 ┌────────────────┐   ┌────────────────────┐
                 │     MySQL      │   │   报表文件目录       │
                 │                │   │ reports/daily       │
                 │ - 关键词表      │   │ reports/weekly      │
                 │ - 商品快照表    │   │ reports/monthly     │
                 │ - 统计结果表    │   └────────────────────┘
                 └────────────────┘
```

---

## 5. 运行环境与资源评估

### 5.1 目标服务器

- CPU：2 核
- 内存：2 GB
- 磁盘：20 GB 以上建议
- 操作系统：Ubuntu / CentOS / Debian 任一 Linux 发行版

### 5.2 第一版资源结论

2 核 2G 可以支撑第一版，前提如下：

- 关键词规模控制在 30～100 个
- 每天运行 2～3 次采集
- 每个关键词只采前 20～50 条结果
- 不使用大量浏览器实例并发抓取
- 不部署前端与额外中间件

### 5.3 资源消耗估算

| 模块 | 资源占用估算 |
|---|---:|
| Linux 系统基础 | 300MB ～ 500MB |
| MySQL | 200MB ～ 500MB |
| Python 运行时 | 100MB ～ 300MB |
| 统计导出阶段 | 100MB ～ 300MB |
| 总体可控范围 | 1GB ～ 1.6GB 左右 |

说明：
- 若采集依赖大量浏览器自动化，2G 内存会比较吃紧。
- 第一版建议优先采用轻量请求方式或极低并发浏览器抓取。

---

## 6. 技术选型

### 6.1 核心技术栈

- Python 3.11
- MySQL 8.x
- pandas
- openpyxl
- SQLAlchemy 或 PyMySQL
- cron
- logging

### 6.2 可选库建议

- requests / httpx：轻量请求
- beautifulsoup4 / lxml：HTML 解析
- Playwright：仅在必要时用于少量页面渲染抓取
- jieba：中文分词
- rapidfuzz：标题近似匹配

### 6.3 不建议在第一版使用

- Redis
- Celery
- Kafka
- Elasticsearch
- Kubernetes
- Vue / React 前端
- FastAPI API 服务

---

## 7. 系统模块设计

### 7.1 关键词配置模块

职责：

- 维护要监控的关键词列表
- 给关键词打分类标签
- 支持启用 / 停用

示例分类：

- 小学资料
- 初中资料
- 高中资料
- 高考资料
- 考研资料
- 考公资料
- 考编资料
- 教资资料
- 大学资料

### 7.2 数据采集模块

职责：

- 按关键词抓取搜索结果
- 解析商品卡片信息
- 提取基础字段
- 写入商品快照表
- 控制采集频率与去重

第一版建议采集字段：

- 抓取日期
- 抓取时间
- keyword
- 排名位置
- 商品标题
- 商品链接
- 商品价格
- 卖家昵称
- 商品描述摘要（若能拿到）
- item_id（若能稳定提取）

### 7.3 数据清洗模块

职责：

- 去除空值和异常值
- 标准化价格字段
- 标准化关键词归属
- 去除明显重复商品
- 清洗标题噪声词

可清洗的噪声词示例：

- 秒发
- 自动发货
- 全网最低
- 亏本冲量
- 引流
- 低价
- 高清
- 全套
- 最新版

### 7.4 统计分析模块

职责：

- 计算每日热度指标
- 计算价格统计指标
- 计算趋势变化
- 计算机会值
- 输出日 / 周 / 月统计结果

### 7.5 报表导出模块

职责：

- 导出 Excel 报表
- 导出 CSV 报表
- 按日期归档报表
- 生成统一命名规则

### 7.6 定时调度模块

职责：

- 每天执行采集任务
- 每天生成日报
- 每周生成周报
- 每月生成月报
- 写日志与错误记录

---

## 8. 数据流程

### 8.1 每日流程

1. 读取关键词配置表
2. 针对启用状态的关键词执行采集
3. 将采集结果写入 `item_snapshot`
4. 基于当日快照数据计算 `keyword_daily_stats`
5. 生成日报 Excel / CSV
6. 写入运行日志

### 8.2 每周流程

1. 读取最近两周统计数据
2. 计算本周 vs 上周变化
3. 生成周报

### 8.3 每月流程

1. 读取最近两个月统计数据
2. 计算本月 vs 上月变化
3. 生成月报

---

## 9. 数据库设计

### 9.1 关键词配置表 `keyword_config`

```sql
CREATE TABLE keyword_config (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    keyword VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    status TINYINT NOT NULL DEFAULT 1,
    priority INT NOT NULL DEFAULT 100,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_keyword (keyword)
);
```

字段说明：

- `keyword`：监控关键词
- `category`：所属大类
- `status`：是否启用，1=启用，0=停用
- `priority`：优先级，数字越小越优先

### 9.2 商品快照表 `item_snapshot`

```sql
CREATE TABLE item_snapshot (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    snapshot_date DATE NOT NULL,
    snapshot_time DATETIME NOT NULL,
    keyword VARCHAR(100) NOT NULL,
    item_id VARCHAR(100) DEFAULT NULL,
    title VARCHAR(500) NOT NULL,
    price DECIMAL(10,2) DEFAULT NULL,
    rank_pos INT DEFAULT NULL,
    seller_name VARCHAR(100) DEFAULT NULL,
    item_url VARCHAR(1000) DEFAULT NULL,
    desc_text TEXT,
    raw_text TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_date_keyword (snapshot_date, keyword),
    INDEX idx_keyword (keyword),
    INDEX idx_item_id (item_id)
);
```

字段说明：

- `snapshot_date`：快照日期
- `snapshot_time`：采集时间
- `keyword`：触发采集的关键词
- `item_id`：商品唯一标识，若无法提取可为空
- `rank_pos`：在本次搜索结果中的排名

### 9.3 每日统计表 `keyword_daily_stats`

```sql
CREATE TABLE keyword_daily_stats (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    stat_date DATE NOT NULL,
    keyword VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    item_count INT DEFAULT 0,
    avg_price DECIMAL(10,2) DEFAULT NULL,
    min_price DECIMAL(10,2) DEFAULT NULL,
    max_price DECIMAL(10,2) DEFAULT NULL,
    top10_avg_rank DECIMAL(10,2) DEFAULT NULL,
    hot_score DECIMAL(10,2) DEFAULT NULL,
    trend_up_down DECIMAL(10,2) DEFAULT NULL,
    opportunity_score DECIMAL(10,2) DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_stat_date_keyword (stat_date, keyword),
    INDEX idx_stat_date (stat_date),
    INDEX idx_keyword (keyword)
);
```

字段说明：

- `item_count`：当日该关键词抓到的商品数
- `avg_price` / `min_price` / `max_price`：价格分布
- `top10_avg_rank`：Top10 排名均值
- `hot_score`：热度分
- `trend_up_down`：相较前一日的变化值
- `opportunity_score`：机会值

### 9.4 每日商品评分表 `item_score_daily`

```sql
CREATE TABLE item_score_daily (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    stat_date DATE NOT NULL,
    keyword VARCHAR(100) NOT NULL,
    item_id VARCHAR(100) DEFAULT NULL,
    title VARCHAR(500) NOT NULL,
    rank_pos INT DEFAULT NULL,
    price DECIMAL(10,2) DEFAULT NULL,
    score DECIMAL(10,2) DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_stat_date_keyword (stat_date, keyword),
    INDEX idx_stat_date (stat_date)
);
```

用途：

- 输出某关键词下的商品强度榜
- 支撑日报的 Top 商品榜单

---

## 10. 指标设计

### 10.1 每日基础指标

每个关键词每日统计以下指标：

- 商品数 `item_count`
- 平均价格 `avg_price`
- 最低价 `min_price`
- 最高价 `max_price`
- Top10 平均排名 `top10_avg_rank`

### 10.2 热度分 `hot_score`

建议第一版采用简化公式：

```text
hot_score = item_count * 0.4 + top_item_score_avg * 0.4 + new_item_ratio * 0.2
```

若第一版没有稳定的新商品识别能力，可先简化为：

```text
hot_score = item_count * 0.6 + rank_factor * 0.4
```

### 10.3 趋势值 `trend_up_down`

```text
trend_up_down = 今日 hot_score - 昨日 hot_score
```

也可同步计算趋势百分比：

```text
trend_rate = (今日 hot_score - 昨日 hot_score) / 昨日 hot_score
```

### 10.4 机会值 `opportunity_score`

第一版建议采用可解释的简化公式：

```text
opportunity_score = hot_score * (1 + trend_rate) / (1 + competition_factor)
```

其中：

- `competition_factor` 可由 `item_count` 或价格带拥挤程度近似表示。

### 10.5 商品评分 `score`

第一版建议简化为：

```text
score = rank_score * 0.5 + title_match_score * 0.3 + price_score * 0.2
```

说明：

- `rank_score`：排名越靠前分数越高
- `title_match_score`：标题与关键词越匹配越高
- `price_score`：价格处于合理区间时分数较高

---

## 11. 报表设计

### 11.1 日报

输出文件示例：

- `daily_keyword_report_YYYY-MM-DD.xlsx`
- `daily_item_report_YYYY-MM-DD.xlsx`

建议包含以下 Sheet：

#### Sheet1：关键词热度榜
字段：

- 日期
- 类目
- 关键词
- 商品数
- 平均价格
- 热度分
- 较昨日变化
- 机会值

#### Sheet2：关键词价格分布
字段：

- 日期
- 关键词
- 最低价
- 平均价
- 最高价
- 样本数

#### Sheet3：商品强度榜
字段：

- 日期
- 关键词
- 商品标题
- 价格
- 排名
- 评分
- 链接

### 11.2 周报

输出文件示例：

- `weekly_trend_report_YYYY-WW.xlsx`

建议字段：

- 关键词
- 本周热度均值
- 上周热度均值
- 周环比
- 本周均价
- 上周均价
- 建议关注等级

### 11.3 月报

输出文件示例：

- `monthly_trend_report_YYYY-MM.xlsx`

建议字段：

- 类目
- 关键词
- 本月热度均值
- 上月热度均值
- 月环比
- 本月均价
- 上月均价
- 是否进入上升期

---

## 12. 目录结构建议

```text
xianyu_report_system/
├── config/
│   └── settings.py
├── db/
│   ├── mysql_client.py
│   └── init.sql
├── crawler/
│   ├── crawl_keywords.py
│   └── parser.py
├── analyzer/
│   ├── clean_data.py
│   ├── calc_daily_stats.py
│   ├── calc_weekly_stats.py
│   ├── calc_monthly_stats.py
│   └── scoring.py
├── exporter/
│   ├── export_excel.py
│   └── export_csv.py
├── reports/
│   ├── daily/
│   ├── weekly/
│   └── monthly/
├── logs/
├── scheduler/
│   └── cron_example.txt
├── main_daily.py
├── main_weekly.py
├── main_monthly.py
├── requirements.txt
└── README.md
```

---

## 13. 脚本职责建议

### 13.1 `main_daily.py`

职责：

- 读取启用关键词
- 执行采集
- 写入快照表
- 执行每日统计
- 导出日报

### 13.2 `main_weekly.py`

职责：

- 汇总最近两周数据
- 生成周对比结果
- 导出周报

### 13.3 `main_monthly.py`

职责：

- 汇总最近两个月数据
- 生成月对比结果
- 导出月报

---

## 14. 定时任务建议

### 14.1 日常采集与日报

建议每天 2～3 次采集，晚间生成日报。

示例 cron：

```bash
0 9,15,21 * * * /usr/bin/python3 /opt/xianyu_report_system/main_daily.py >> /opt/xianyu_report_system/logs/daily.log 2>&1
```

若担心重复生成日报，可拆为两类任务：

- 白天只采集
- 夜间统计 + 导出

例如：

```bash
0 9,15 * * * /usr/bin/python3 /opt/xianyu_report_system/main_daily.py --mode crawl >> /opt/xianyu_report_system/logs/daily_crawl.log 2>&1
30 21 * * * /usr/bin/python3 /opt/xianyu_report_system/main_daily.py --mode report >> /opt/xianyu_report_system/logs/daily_report.log 2>&1
```

### 14.2 周报

```bash
30 23 * * 1 /usr/bin/python3 /opt/xianyu_report_system/main_weekly.py >> /opt/xianyu_report_system/logs/weekly.log 2>&1
```

### 14.3 月报

```bash
0 1 1 * * /usr/bin/python3 /opt/xianyu_report_system/main_monthly.py >> /opt/xianyu_report_system/logs/monthly.log 2>&1
```

---

## 15. 采集策略建议

### 15.1 第一版关键词规模

建议从 30～50 个关键词起步，后续逐步扩展到 100 个左右。

### 15.2 每次采集范围

建议每个关键词采集前 20～50 条商品即可。

### 15.3 采集频率

建议：

- 每天 2 次：适合极轻量
- 每天 3 次：适合常规版

### 15.4 并发控制

建议第一版使用：

- 单线程
- 或极低并发（例如 2～5 并发）

不建议第一版做高并发采集。

### 15.5 错误处理

建议加入：

- 请求失败重试 1～3 次
- 单关键词采集失败不影响全局流程
- 记录失败关键词与失败原因

---

## 16. 日志设计

建议输出以下日志：

- 程序启动日志
- 本次采集关键词数
- 每个关键词采集条数
- 入库成功条数
- 统计成功日志
- 导出文件路径
- 异常堆栈日志

日志文件建议：

- `logs/daily.log`
- `logs/weekly.log`
- `logs/monthly.log`
- `logs/error.log`

---

## 17. 代码实现建议

### 17.1 开发原则

- 模块化设计
- 配置与代码分离
- 表结构稳定优先
- 先实现全链路跑通，再迭代评分算法

### 17.2 关键实现顺序

建议 AI Agent 按以下顺序开发：

1. 建立 MySQL 表结构
2. 实现关键词读取模块
3. 实现基础采集模块
4. 实现快照入库
5. 实现每日统计逻辑
6. 实现 Excel / CSV 导出
7. 实现周报 / 月报逻辑
8. 实现日志与 cron 运行支持

### 17.3 评分与趋势逻辑建议

第一版不追求复杂机器学习模型，只使用简单可解释公式即可。

---

## 18. 风险与限制

### 18.1 数据层面限制

第一版更适合做“热度趋势、竞争强度、价格分布、关键词机会”的估算分析，不宜将结果表述为“官方真实销量榜”。

### 18.2 平台变化风险

若目标页面结构变化，解析逻辑需要调整。

### 18.3 反爬与频率控制

应避免高频、大规模自动抓取。

### 18.4 服务器资源限制

在 2 核 2G 条件下，不宜引入重型依赖和高并发浏览器抓取。

---

## 19. 第一版交付物

建议 AI Agent 最终交付以下内容：

1. Python 项目源码
2. MySQL 初始化 SQL
3. requirements.txt
4. README.md
5. cron 配置示例
6. 示例报表输出
7. 日志输出示例

---

## 20. 第二版可扩展方向（非本次必须）

后续若第一版跑通，可升级：

- 增加资源池覆盖率分析
- 增加标题模板分析
- 增加更细类目词库
- 增加详情页深度解析
- 增加自动化选词扩词能力
- 增加简单 Web 查询界面
- 升级到 4C8G 后增加 Redis / API 服务

---

## 21. 给 AI Agent 的一句话开发指令

请基于本方案实现一个“闲鱼教育资料关键词趋势采集与报表系统”第一版：

- 使用 Python + MySQL
- 不做前端
- 通过 cron 定时运行
- 支持关键词采集、快照入库、日/周/月统计、Excel/CSV 报表导出
- 代码结构清晰，便于后续扩展
- 默认兼容 2 核 2G Linux 云服务器环境

