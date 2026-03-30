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
