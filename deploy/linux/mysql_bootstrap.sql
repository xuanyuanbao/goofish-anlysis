CREATE DATABASE IF NOT EXISTS xianyu_report
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'xianyu'@'%' IDENTIFIED BY 'xianyu123456';
GRANT ALL PRIVILEGES ON xianyu_report.* TO 'xianyu'@'%';
FLUSH PRIVILEGES;

USE xianyu_report;

CREATE TABLE IF NOT EXISTS keyword_config (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    keyword VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    status TINYINT NOT NULL DEFAULT 1,
    priority INT NOT NULL DEFAULT 100,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_keyword (keyword)
);

CREATE TABLE IF NOT EXISTS item_snapshot (
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
    raw_text LONGTEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_date_keyword (snapshot_date, keyword),
    INDEX idx_item_id (item_id)
);

CREATE TABLE IF NOT EXISTS keyword_daily_stats (
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

CREATE TABLE IF NOT EXISTS item_score_daily (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    stat_date DATE NOT NULL,
    keyword VARCHAR(100) NOT NULL,
    item_id VARCHAR(100) DEFAULT NULL,
    title VARCHAR(500) NOT NULL,
    rank_pos INT DEFAULT NULL,
    price DECIMAL(10,2) DEFAULT NULL,
    score DECIMAL(10,2) DEFAULT NULL,
    item_url VARCHAR(1000) DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_stat_date_keyword (stat_date, keyword),
    INDEX idx_stat_date (stat_date)
);

CREATE TABLE IF NOT EXISTS job_run_history (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    run_id VARCHAR(80) NOT NULL,
    job_name VARCHAR(20) NOT NULL,
    run_mode VARCHAR(20) NOT NULL,
    run_status VARCHAR(20) NOT NULL,
    target_label VARCHAR(40) DEFAULT NULL,
    snapshot_date DATE DEFAULT NULL,
    started_at DATETIME NOT NULL,
    finished_at DATETIME NOT NULL,
    duration_seconds DECIMAL(10,2) NOT NULL DEFAULT 0,
    keyword_total INT NOT NULL DEFAULT 0,
    keyword_success INT NOT NULL DEFAULT 0,
    keyword_failed INT NOT NULL DEFAULT 0,
    inserted_snapshots INT NOT NULL DEFAULT 0,
    daily_stats INT NOT NULL DEFAULT 0,
    item_scores INT NOT NULL DEFAULT 0,
    alert_level VARCHAR(20) NOT NULL DEFAULT 'info',
    alert_message TEXT,
    report_paths_json JSON DEFAULT NULL,
    metadata_json LONGTEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_run_id (run_id),
    INDEX idx_job_started_at (job_name, started_at),
    INDEX idx_snapshot_date (snapshot_date)
);

CREATE TABLE IF NOT EXISTS keyword_failure_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    run_id VARCHAR(80) NOT NULL,
    job_name VARCHAR(20) NOT NULL,
    snapshot_date DATE DEFAULT NULL,
    keyword VARCHAR(100) NOT NULL,
    category VARCHAR(50) DEFAULT NULL,
    error_type VARCHAR(100) NOT NULL,
    error_message TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_run_id (run_id),
    INDEX idx_keyword_snapshot (keyword, snapshot_date)
);

CREATE TABLE IF NOT EXISTS data_quality_issue (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    run_id VARCHAR(80) NOT NULL,
    snapshot_date DATE DEFAULT NULL,
    keyword VARCHAR(100) NOT NULL,
    item_id VARCHAR(100) DEFAULT NULL,
    issue_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    issue_message TEXT NOT NULL,
    sample_value TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_quality_run_id (run_id),
    INDEX idx_quality_snapshot (snapshot_date, keyword),
    INDEX idx_quality_issue_type (issue_type)
);
