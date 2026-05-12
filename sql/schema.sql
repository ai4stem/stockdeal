-- stockdeal MySQL schema
-- Engine: InnoDB, charset: utf8mb4
-- Time storage: all timestamps in UTC; UI converts to Asia/Seoul.

SET NAMES utf8mb4;
SET time_zone = '+00:00';

CREATE DATABASE IF NOT EXISTS stockdeal
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;
USE stockdeal;

-- =========================================================================
-- Reference: tickers
-- =========================================================================
CREATE TABLE IF NOT EXISTS ticker (
  ticker          VARCHAR(12) PRIMARY KEY,
  name            VARCHAR(64) NOT NULL,
  market          VARCHAR(16) NOT NULL,        -- KOSPI, KOSDAQ, NYSE...
  sector          VARCHAR(64),
  corp_code       VARCHAR(16),                  -- DART 고유번호
  is_watchlist    TINYINT(1) NOT NULL DEFAULT 0,
  created_at      DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- =========================================================================
-- Macro indicators (daily / monthly)
-- =========================================================================
CREATE TABLE IF NOT EXISTS macro_indicator (
  code            VARCHAR(64) PRIMARY KEY,      -- e.g. FRED:DGS10, ECOS:722Y001
  source          VARCHAR(16) NOT NULL,         -- FRED | ECOS | MANUAL
  name            VARCHAR(128) NOT NULL,
  unit            VARCHAR(32),
  frequency       VARCHAR(16),                  -- DAILY | MONTHLY | QUARTERLY
  description     VARCHAR(255)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS macro_observation (
  code            VARCHAR(64) NOT NULL,
  observed_at     DATE        NOT NULL,
  value           DOUBLE      NOT NULL,
  ingested_at     DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (code, observed_at),
  CONSTRAINT fk_macro_obs_code FOREIGN KEY (code) REFERENCES macro_indicator(code)
) ENGINE=InnoDB;

-- =========================================================================
-- Price data
-- =========================================================================
-- Tick-level trades (rolling 7 days; trim via scheduled EVENT)
CREATE TABLE IF NOT EXISTS tick_trade (
  id              BIGINT NOT NULL AUTO_INCREMENT,
  ticker          VARCHAR(12) NOT NULL,
  ts              DATETIME(3) NOT NULL,
  price           DECIMAL(15,2) NOT NULL,
  qty             INT NOT NULL,
  side            CHAR(1),                      -- B(매수체결) / S(매도체결) / NULL
  cum_volume      BIGINT,
  PRIMARY KEY (id, ts),
  KEY idx_tick_ticker_ts (ticker, ts)
) ENGINE=InnoDB
  PARTITION BY RANGE (TO_DAYS(ts)) (
    PARTITION p_init VALUES LESS THAN MAXVALUE
  );

-- 1-minute bars (long-term retention)
CREATE TABLE IF NOT EXISTS bar_1m (
  ticker          VARCHAR(12) NOT NULL,
  ts              DATETIME    NOT NULL,
  open            DECIMAL(15,2) NOT NULL,
  high            DECIMAL(15,2) NOT NULL,
  low             DECIMAL(15,2) NOT NULL,
  close           DECIMAL(15,2) NOT NULL,
  volume          BIGINT      NOT NULL,
  trade_value     DECIMAL(20,2),
  buy_strength    DOUBLE,                       -- 매수체결량 / (매수+매도)
  PRIMARY KEY (ticker, ts)
) ENGINE=InnoDB;

-- Daily bars (permanent)
CREATE TABLE IF NOT EXISTS bar_daily (
  ticker          VARCHAR(12) NOT NULL,
  trade_date      DATE        NOT NULL,
  open            DECIMAL(15,2) NOT NULL,
  high            DECIMAL(15,2) NOT NULL,
  low             DECIMAL(15,2) NOT NULL,
  close           DECIMAL(15,2) NOT NULL,
  volume          BIGINT      NOT NULL,
  trade_value     DECIMAL(20,2),
  foreign_net     BIGINT,                       -- 외국인 순매수 (주식수)
  inst_net        BIGINT,                       -- 기관 순매수
  individual_net  BIGINT,                       -- 개인 순매수
  short_volume    BIGINT,                       -- 공매도량
  short_balance   BIGINT,                       -- 공매도잔고
  PRIMARY KEY (ticker, trade_date)
) ENGINE=InnoDB;

-- =========================================================================
-- Fundamentals & disclosures (DART)
-- =========================================================================
CREATE TABLE IF NOT EXISTS company_financial (
  ticker          VARCHAR(12) NOT NULL,
  period_end      DATE        NOT NULL,         -- 결산일
  period_type     VARCHAR(8)  NOT NULL,         -- Q1/Q2/Q3/Q4/ANNUAL
  account_code    VARCHAR(32) NOT NULL,
  account_name    VARCHAR(128),
  value           DECIMAL(20,2),
  unit            VARCHAR(16) DEFAULT 'KRW',
  source_rcept_no VARCHAR(32),
  PRIMARY KEY (ticker, period_end, period_type, account_code)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS disclosure (
  rcept_no        VARCHAR(32) PRIMARY KEY,
  ticker          VARCHAR(12) NOT NULL,
  corp_code       VARCHAR(16),
  filed_at        DATETIME    NOT NULL,
  report_type     VARCHAR(64),                  -- 정기보고서, 주요사항보고 등
  title           VARCHAR(255) NOT NULL,
  url             VARCHAR(512),
  raw_payload     LONGTEXT,                     -- XML/HTML stash
  summary_json    JSON,                         -- LLM 요약 결과
  importance      TINYINT,                      -- 1~5
  ingested_at     DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  analyzed_at     DATETIME,
  KEY idx_disclosure_ticker_filed (ticker, filed_at)
) ENGINE=InnoDB;

-- =========================================================================
-- News
-- =========================================================================
CREATE TABLE IF NOT EXISTS news_raw (
  id              BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  source          VARCHAR(64) NOT NULL,         -- finnhub | naver | rss:reuters ...
  external_id     VARCHAR(255),                 -- source-side unique id
  url             VARCHAR(1024) NOT NULL,
  url_hash        CHAR(64) NOT NULL,            -- sha256(url) for dedup
  title           VARCHAR(512) NOT NULL,
  body            MEDIUMTEXT,
  published_at    DATETIME,
  language        VARCHAR(8),
  fetched_at      DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_news_url_hash (url_hash),
  KEY idx_news_published (published_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS news_analyzed (
  news_id         BIGINT PRIMARY KEY,
  importance      TINYINT NOT NULL,              -- 1~5
  sentiment       DECIMAL(4,3),                  -- -1.0 ~ 1.0
  horizon         VARCHAR(16),                   -- INTRADAY | SHORT | MID | LONG
  tickers         JSON,                          -- ["403870","005930"]
  summary         TEXT,
  rationale       TEXT,
  llm_model       VARCHAR(64),
  analyzed_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_news_analyzed_news FOREIGN KEY (news_id) REFERENCES news_raw(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- =========================================================================
-- Strategy & trading
-- =========================================================================
CREATE TABLE IF NOT EXISTS trading_mode_history (
  id              BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  mode            VARCHAR(16) NOT NULL,          -- OFF/SIMULATION/CONFIRM/AUTO
  changed_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  changed_by      VARCHAR(64),
  reason          VARCHAR(255)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS signal (
  signal_id       BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  ticker          VARCHAR(12) NOT NULL,
  ts              DATETIME NOT NULL,
  strategy        VARCHAR(64) NOT NULL,
  action          VARCHAR(8)  NOT NULL,          -- BUY/SELL/HOLD
  confidence      DECIMAL(4,3),
  horizon         VARCHAR(16),                   -- INTRADAY/SHORT/MID/LONG
  reasoning_text  TEXT,
  features_snapshot JSON,
  llm_model       VARCHAR(64),
  KEY idx_signal_ticker_ts (ticker, ts)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS order_intent (
  intent_id       BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  signal_id       BIGINT,
  ticker          VARCHAR(12) NOT NULL,
  side            VARCHAR(8)  NOT NULL,          -- BUY/SELL
  qty             INT         NOT NULL,
  price           DECIMAL(15,2),                  -- NULL for market
  order_type      VARCHAR(16) NOT NULL,           -- MARKET/LIMIT
  status          VARCHAR(24) NOT NULL,           -- pending_confirm/approved/rejected/expired/executed/failed
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  expires_at      DATETIME,
  responded_at    DATETIME,
  response_channel VARCHAR(16),                   -- telegram/kakao/api
  reject_reason   VARCHAR(255),
  CONSTRAINT fk_intent_signal FOREIGN KEY (signal_id) REFERENCES signal(signal_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS trade_real (
  id              BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  signal_id       BIGINT,
  intent_id       BIGINT,
  kis_order_id    VARCHAR(32),
  ticker          VARCHAR(12) NOT NULL,
  side            VARCHAR(8) NOT NULL,
  qty             INT NOT NULL,
  fill_price      DECIMAL(15,2) NOT NULL,
  fill_qty        INT NOT NULL,
  fill_ts         DATETIME NOT NULL,
  commission      DECIMAL(15,2) DEFAULT 0,
  tax             DECIMAL(15,2) DEFAULT 0,
  pnl             DECIMAL(15,2),
  KEY idx_trade_real_signal (signal_id),
  KEY idx_trade_real_ticker_ts (ticker, fill_ts)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS trade_paper (
  id              BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  signal_id       BIGINT,
  ticker          VARCHAR(12) NOT NULL,
  side            VARCHAR(8) NOT NULL,
  qty             INT NOT NULL,
  fill_price      DECIMAL(15,2) NOT NULL,
  fill_qty        INT NOT NULL,
  fill_ts         DATETIME NOT NULL,
  commission      DECIMAL(15,2) DEFAULT 0,
  tax             DECIMAL(15,2) DEFAULT 0,
  pnl             DECIMAL(15,2),
  slippage_assumed DECIMAL(6,4),
  KEY idx_trade_paper_signal (signal_id),
  KEY idx_trade_paper_ticker_ts (ticker, fill_ts)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS position (
  ticker          VARCHAR(12) NOT NULL,
  book            VARCHAR(8)  NOT NULL,          -- REAL/PAPER
  qty             INT NOT NULL DEFAULT 0,
  avg_cost        DECIMAL(15,2) NOT NULL DEFAULT 0,
  updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (ticker, book)
) ENGINE=InnoDB;

-- =========================================================================
-- Learning loop
-- =========================================================================
CREATE TABLE IF NOT EXISTS decision_outcome (
  id              BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  signal_id       BIGINT NOT NULL,
  horizon_days    INT NOT NULL,                  -- 5 / 20 / 60
  realized_return DECIMAL(8,5),
  outcome_label   VARCHAR(16),                   -- correct/wrong/partial
  evaluated_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_outcome_signal_horizon (signal_id, horizon_days),
  CONSTRAINT fk_outcome_signal FOREIGN KEY (signal_id) REFERENCES signal(signal_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS lessons_learned (
  id              BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  category        VARCHAR(64),                   -- timing/sizing/macro/sector
  insight_text    TEXT NOT NULL,
  supporting_decision_ids JSON,
  confidence_score DECIMAL(4,3),
  active          TINYINT(1) NOT NULL DEFAULT 1,
  retired_at      DATETIME,
  retired_reason  VARCHAR(255)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS model_registry (
  id              BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  model_type      VARCHAR(64) NOT NULL,          -- patchtst / xgb_factor / ...
  version         VARCHAR(32) NOT NULL,
  trained_at      DATETIME NOT NULL,
  train_window_start DATE,
  train_window_end   DATE,
  val_sharpe      DECIMAL(8,4),
  val_mae         DECIMAL(12,6),
  artifact_path   VARCHAR(512),
  active          TINYINT(1) NOT NULL DEFAULT 0,
  notes           TEXT,
  UNIQUE KEY uk_model_type_version (model_type, version)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS strategy_params (
  id              BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  strategy_name   VARCHAR(64) NOT NULL,
  params          JSON NOT NULL,
  effective_from  DATETIME NOT NULL,
  effective_to    DATETIME,
  source          VARCHAR(16) NOT NULL,          -- manual/auto_tuned
  KEY idx_strategy_params_name_from (strategy_name, effective_from)
) ENGINE=InnoDB;

-- =========================================================================
-- Notifications log
-- =========================================================================
CREATE TABLE IF NOT EXISTS notification_log (
  id              BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  ts              DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  channel         VARCHAR(16) NOT NULL,          -- telegram/kakao/email
  level           VARCHAR(8)  NOT NULL,          -- INFO/WARN/CRIT
  subject         VARCHAR(255),
  payload         MEDIUMTEXT,
  delivered       TINYINT(1) NOT NULL DEFAULT 0,
  error           VARCHAR(512)
) ENGINE=InnoDB;
