CREATE TABLE IF NOT EXISTS keyword_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,
    status INTEGER NOT NULL DEFAULT 1,
    priority INTEGER NOT NULL DEFAULT 100,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS item_snapshot (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_date TEXT NOT NULL,
    snapshot_time TEXT NOT NULL,
    keyword TEXT NOT NULL,
    item_id TEXT,
    title TEXT NOT NULL,
    price REAL,
    rank_pos INTEGER,
    seller_name TEXT,
    item_url TEXT,
    desc_text TEXT,
    raw_text TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_item_snapshot_date_keyword
ON item_snapshot (snapshot_date, keyword);

CREATE INDEX IF NOT EXISTS idx_item_snapshot_item_id
ON item_snapshot (item_id);

CREATE TABLE IF NOT EXISTS keyword_daily_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stat_date TEXT NOT NULL,
    keyword TEXT NOT NULL,
    category TEXT NOT NULL,
    item_count INTEGER NOT NULL DEFAULT 0,
    avg_price REAL,
    min_price REAL,
    max_price REAL,
    top10_avg_rank REAL,
    hot_score REAL NOT NULL DEFAULT 0,
    trend_up_down REAL NOT NULL DEFAULT 0,
    opportunity_score REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (stat_date, keyword)
);

CREATE INDEX IF NOT EXISTS idx_keyword_daily_stats_stat_date
ON keyword_daily_stats (stat_date);

CREATE TABLE IF NOT EXISTS item_score_daily (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stat_date TEXT NOT NULL,
    keyword TEXT NOT NULL,
    item_id TEXT,
    title TEXT NOT NULL,
    rank_pos INTEGER,
    price REAL,
    score REAL NOT NULL DEFAULT 0,
    item_url TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_item_score_daily_stat_date_keyword
ON item_score_daily (stat_date, keyword);

CREATE TABLE IF NOT EXISTS job_run_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL UNIQUE,
    job_name TEXT NOT NULL,
    run_mode TEXT NOT NULL,
    run_status TEXT NOT NULL,
    target_label TEXT,
    snapshot_date TEXT,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    duration_seconds REAL NOT NULL DEFAULT 0,
    keyword_total INTEGER NOT NULL DEFAULT 0,
    keyword_success INTEGER NOT NULL DEFAULT 0,
    keyword_failed INTEGER NOT NULL DEFAULT 0,
    inserted_snapshots INTEGER NOT NULL DEFAULT 0,
    daily_stats INTEGER NOT NULL DEFAULT 0,
    item_scores INTEGER NOT NULL DEFAULT 0,
    alert_level TEXT NOT NULL DEFAULT 'info',
    alert_message TEXT,
    report_paths_json TEXT,
    metadata_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_job_run_history_job_started
ON job_run_history (job_name, started_at);

CREATE TABLE IF NOT EXISTS keyword_failure_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    job_name TEXT NOT NULL,
    snapshot_date TEXT,
    keyword TEXT NOT NULL,
    category TEXT,
    error_type TEXT NOT NULL,
    error_message TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_keyword_failure_log_run_id
ON keyword_failure_log (run_id);

CREATE TABLE IF NOT EXISTS data_quality_issue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    snapshot_date TEXT,
    keyword TEXT NOT NULL,
    item_id TEXT,
    issue_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    issue_message TEXT NOT NULL,
    sample_value TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_data_quality_issue_run_id
ON data_quality_issue (run_id);
