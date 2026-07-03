-- BotChainVision initial schema
-- Run this in Supabase Dashboard → SQL Editor → New query → Run

-- Supply chain categories (from settings)
CREATE TABLE IF NOT EXISTS supply_chain_categories (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    component_examples TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Supply chain vendors (from settings)
CREATE TABLE IF NOT EXISTS supply_chain_vendors (
    id              SERIAL PRIMARY KEY,
    category_id     TEXT NOT NULL REFERENCES supply_chain_categories(id),
    company         TEXT NOT NULL,
    ticker          TEXT NOT NULL,
    market          TEXT NOT NULL DEFAULT 'TW',
    watch           BOOLEAN NOT NULL DEFAULT TRUE,
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(category_id, ticker)
);

-- Daily OHLCV + MA20
CREATE TABLE IF NOT EXISTS daily_prices (
    id              SERIAL PRIMARY KEY,
    ticker          TEXT NOT NULL,
    trade_date      DATE NOT NULL,
    open_price      DOUBLE PRECISION,
    high_price      DOUBLE PRECISION NOT NULL,
    low_price       DOUBLE PRECISION NOT NULL,
    close_price     DOUBLE PRECISION NOT NULL,
    volume          BIGINT,
    ma20            DOUBLE PRECISION,
    source          TEXT DEFAULT 'scheduled',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(ticker, trade_date)
);

CREATE INDEX IF NOT EXISTS idx_daily_prices_ticker_date ON daily_prices(ticker, trade_date DESC);

-- Historical dividends
CREATE TABLE IF NOT EXISTS dividends (
    id              SERIAL PRIMARY KEY,
    ticker          TEXT NOT NULL,
    ex_date         DATE NOT NULL,
    cash_dividend   DOUBLE PRECISION NOT NULL,
    fiscal_year     INTEGER,
    source_type     TEXT DEFAULT 'yfinance',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(ticker, ex_date)
);

-- Daily dividend yield snapshot (auto-calculated)
CREATE TABLE IF NOT EXISTS dividend_yield_daily (
    id                  SERIAL PRIMARY KEY,
    ticker              TEXT NOT NULL,
    trade_date          DATE NOT NULL,
    close_price         DOUBLE PRECISION NOT NULL,
    trailing_12m_div    DOUBLE PRECISION NOT NULL DEFAULT 0,
    dividend_yield_pct  DOUBLE PRECISION,
    source              TEXT DEFAULT 'scheduled',
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(ticker, trade_date)
);

CREATE INDEX IF NOT EXISTS idx_yield_ticker_date ON dividend_yield_daily(ticker, trade_date DESC);

-- Historical EPS
CREATE TABLE IF NOT EXISTS historical_eps (
    id              SERIAL PRIMARY KEY,
    ticker          TEXT NOT NULL,
    period_type     TEXT NOT NULL,
    fiscal_period   TEXT NOT NULL,
    period_end      DATE,
    eps             DOUBLE PRECISION NOT NULL,
    source_type     TEXT DEFAULT 'yfinance',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(ticker, period_type, fiscal_period)
);

-- Estimates from news / yfinance / manual
CREATE TABLE IF NOT EXISTS estimates (
    id              SERIAL PRIMARY KEY,
    ticker          TEXT NOT NULL,
    estimate_date   DATE NOT NULL,
    fiscal_period   TEXT,
    metric_type     TEXT NOT NULL,
    value           DOUBLE PRECISION,
    unit            TEXT,
    source_type     TEXT NOT NULL,
    source_url      TEXT,
    source_title    TEXT,
    confidence      DOUBLE PRECISION DEFAULT 1.0,
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- News articles
CREATE TABLE IF NOT EXISTS news_articles (
    id              SERIAL PRIMARY KEY,
    ticker          TEXT,
    published_at    TIMESTAMPTZ,
    title           TEXT NOT NULL,
    url             TEXT UNIQUE,
    summary         TEXT,
    fetched_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Sync log for dashboard display
CREATE TABLE IF NOT EXISTS sync_log (
    id              SERIAL PRIMARY KEY,
    sync_type       TEXT NOT NULL,
    source          TEXT NOT NULL DEFAULT 'scheduled',
    tickers_count   INTEGER,
    status          TEXT NOT NULL,
    message         TEXT,
    finished_at     TIMESTAMPTZ DEFAULT NOW()
);

-- RLS: allow service role full access; anon read-only for dashboard
ALTER TABLE supply_chain_categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE supply_chain_vendors ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_prices ENABLE ROW LEVEL SECURITY;
ALTER TABLE dividends ENABLE ROW LEVEL SECURITY;
ALTER TABLE dividend_yield_daily ENABLE ROW LEVEL SECURITY;
ALTER TABLE historical_eps ENABLE ROW LEVEL SECURITY;
ALTER TABLE estimates ENABLE ROW LEVEL SECURITY;
ALTER TABLE news_articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE sync_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "anon_read_categories" ON supply_chain_categories FOR SELECT TO anon USING (true);
CREATE POLICY "anon_read_vendors" ON supply_chain_vendors FOR SELECT TO anon USING (true);
CREATE POLICY "anon_read_daily_prices" ON daily_prices FOR SELECT TO anon USING (true);
CREATE POLICY "anon_read_dividends" ON dividends FOR SELECT TO anon USING (true);
CREATE POLICY "anon_read_yield" ON dividend_yield_daily FOR SELECT TO anon USING (true);
CREATE POLICY "anon_read_eps" ON historical_eps FOR SELECT TO anon USING (true);
CREATE POLICY "anon_read_estimates" ON estimates FOR SELECT TO anon USING (true);
CREATE POLICY "anon_read_news" ON news_articles FOR SELECT TO anon USING (true);
CREATE POLICY "anon_read_sync_log" ON sync_log FOR SELECT TO anon USING (true);
