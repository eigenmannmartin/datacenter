-- Cloudflare D1 schema for the engagement test: pilot orders.
-- Visitor statistics come from Cloudflare Web Analytics, not from this database.
-- Browse the data in the Cloudflare dashboard: Storage & Databases > D1 > rechenbox.
-- Apply with: npx wrangler d1 execute rechenbox --remote --file=schema.sql
-- The deploy workflows apply this file before every deploy, so new tables appear on their own.
-- New columns on an existing table do not: add them as a new table, or run the ALTER TABLE by hand first.

-- One row per order (before 27 November 2026: per reservation of a free pilot slot).
CREATE TABLE IF NOT EXISTS signups (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  ts           TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  name         TEXT NOT NULL,
  company      TEXT NOT NULL,
  email        TEXT NOT NULL,
  phone        TEXT,
  industry     TEXT NOT NULL,
  size         TEXT NOT NULL,
  current_it   TEXT NOT NULL DEFAULT '[]',  -- JSON array
  pains        TEXT NOT NULL DEFAULT '[]',  -- JSON array
  plan         TEXT,                       -- start | business | pro (reservations could also say undecided)
  timeline     TEXT,                       -- reservations only: when a decision was due; orders give a start instead
  price_view   TEXT,
  payment_pref TEXT,                       -- monthly | prepay | purchase (reservations could also say undecided)
  message      TEXT,
  wants_call   INTEGER NOT NULL DEFAULT 0, -- reservations only: the order form does not ask
  lang         TEXT,
  utm_source   TEXT,
  utm_medium   TEXT,
  utm_campaign TEXT,
  ref          TEXT,
  country      TEXT,
  token        TEXT,                       -- private reference for the optional second form step
  details_at   TEXT,                       -- when the optional answers arrived
  recommended_plan TEXT                    -- what the plan picker suggested, if used
);
CREATE INDEX IF NOT EXISTS signups_ts ON signups (ts);
CREATE INDEX IF NOT EXISTS signups_token ON signups (token);
CREATE INDEX IF NOT EXISTS signups_email ON signups (email);

-- What an order holds beyond the plan and the payment. One row per order, joined on signups.token.
-- A table of its own so that existing databases get it without a migration.
CREATE TABLE IF NOT EXISTS order_details (
  token   TEXT PRIMARY KEY,                -- signups.token
  options TEXT NOT NULL DEFAULT '[]',      -- JSON array: offsite (backup copy in a Swiss data centre), ai, storage
  start   TEXT                             -- lt6 | 6to12 | gt12: preferred start, in months from the order
);

-- Migrations for databases created by an earlier version of this file:
--   ALTER TABLE signups ADD COLUMN payment_pref TEXT;
--   ALTER TABLE signups ADD COLUMN token TEXT;
--   ALTER TABLE signups ADD COLUMN details_at TEXT;
--   CREATE INDEX IF NOT EXISTS signups_token ON signups (token);
--   ALTER TABLE signups ADD COLUMN recommended_plan TEXT;
