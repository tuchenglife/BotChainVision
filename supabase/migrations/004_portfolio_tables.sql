-- Portfolio account area: broker imports, realized gains, holdings, dividends

CREATE TABLE IF NOT EXISTS portfolio_realized_trades (
    id                   SERIAL PRIMARY KEY,
    broker               TEXT NOT NULL,
    trade_date           DATE NOT NULL,
    symbol               TEXT NOT NULL,
    stock_name           TEXT NOT NULL,
    trade_type           TEXT,
    quantity             DOUBLE PRECISION,
    sell_price           DOUBLE PRECISION,
    buy_amount           DOUBLE PRECISION,
    sell_amount          DOUBLE PRECISION,
    fee                  DOUBLE PRECISION,
    tax                  DOUBLE PRECISION,
    net_amount           DOUBLE PRECISION,
    realized_pnl         DOUBLE PRECISION NOT NULL,
    return_pct           DOUBLE PRECISION,
    order_id             TEXT,
    currency             TEXT DEFAULT 'TWD',
    source_broker_report TEXT,
    source_file          TEXT NOT NULL,
    source_row_id        INTEGER NOT NULL,
    imported_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(broker, source_file, source_row_id)
);

CREATE INDEX IF NOT EXISTS idx_portfolio_realized_date
    ON portfolio_realized_trades(trade_date DESC, broker);

CREATE TABLE IF NOT EXISTS portfolio_holdings (
    id                   SERIAL PRIMARY KEY,
    broker               TEXT NOT NULL,
    snapshot_date        DATE NOT NULL,
    symbol               TEXT NOT NULL,
    stock_name           TEXT NOT NULL,
    position_type        TEXT,
    quantity             DOUBLE PRECISION,
    available_quantity   DOUBLE PRECISION,
    market_price         DOUBLE PRECISION,
    market_value         DOUBLE PRECISION,
    avg_cost_price       DOUBLE PRECISION,
    trade_avg_price      DOUBLE PRECISION,
    cost_basis           DOUBLE PRECISION,
    unrealized_pnl       DOUBLE PRECISION,
    return_pct           DOUBLE PRECISION,
    estimated_net_amount DOUBLE PRECISION,
    fee_estimate         DOUBLE PRECISION,
    currency             TEXT DEFAULT 'TWD',
    source_broker_report TEXT,
    source_file          TEXT NOT NULL,
    source_row_id        INTEGER NOT NULL,
    imported_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(broker, source_file, source_row_id)
);

CREATE INDEX IF NOT EXISTS idx_portfolio_holdings_snapshot
    ON portfolio_holdings(snapshot_date DESC, broker);

CREATE TABLE IF NOT EXISTS portfolio_dividends (
    id                   SERIAL PRIMARY KEY,
    broker               TEXT NOT NULL,
    ex_dividend_date     DATE NOT NULL,
    pay_date             DATE,
    symbol               TEXT NOT NULL,
    stock_name           TEXT NOT NULL,
    quantity             DOUBLE PRECISION,
    dividend_per_share   DOUBLE PRECISION,
    dividend_income      DOUBLE PRECISION NOT NULL,
    currency             TEXT DEFAULT 'TWD',
    source_broker_report TEXT,
    source_file          TEXT NOT NULL,
    source_row_id        INTEGER NOT NULL,
    imported_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(broker, source_file, source_row_id)
);

CREATE INDEX IF NOT EXISTS idx_portfolio_dividends_date
    ON portfolio_dividends(ex_dividend_date DESC, broker);

ALTER TABLE portfolio_realized_trades ENABLE ROW LEVEL SECURITY;
ALTER TABLE portfolio_holdings ENABLE ROW LEVEL SECURITY;
ALTER TABLE portfolio_dividends ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'portfolio_realized_trades'
          AND policyname = 'anon_read_portfolio_realized'
    ) THEN
        CREATE POLICY "anon_read_portfolio_realized"
            ON portfolio_realized_trades FOR SELECT TO anon USING (true);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'portfolio_holdings'
          AND policyname = 'anon_read_portfolio_holdings'
    ) THEN
        CREATE POLICY "anon_read_portfolio_holdings"
            ON portfolio_holdings FOR SELECT TO anon USING (true);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'portfolio_dividends'
          AND policyname = 'anon_read_portfolio_dividends'
    ) THEN
        CREATE POLICY "anon_read_portfolio_dividends"
            ON portfolio_dividends FOR SELECT TO anon USING (true);
    END IF;
END $$;
