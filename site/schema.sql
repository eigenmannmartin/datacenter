-- Cloudflare D1 schema for the engagement test.
-- Apply with: npx wrangler d1 execute rechenbox --remote --file=schema.sql

CREATE TABLE IF NOT EXISTS events (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  ts           TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  pid          TEXT NOT NULL,           -- random id per page load, never stored on the device
  name         TEXT NOT NULL,
  props        TEXT NOT NULL DEFAULT '{}',
  lang         TEXT,
  path         TEXT,
  ref          TEXT,                    -- referrer host only
  utm_source   TEXT,
  utm_medium   TEXT,
  utm_campaign TEXT,
  utm_content  TEXT,
  country      TEXT,
  vw           INTEGER                  -- viewport width, for mobile vs desktop
);
CREATE INDEX IF NOT EXISTS events_name_ts ON events (name, ts);
CREATE INDEX IF NOT EXISTS events_pid ON events (pid);

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
  plan         TEXT,
  timeline     TEXT,
  price_view   TEXT,
  payment_pref TEXT,                       -- monthly | prepay | purchase | undecided
  message      TEXT,
  wants_call   INTEGER NOT NULL DEFAULT 0,
  lang         TEXT,
  utm_source   TEXT,
  utm_medium   TEXT,
  utm_campaign TEXT,
  ref          TEXT,
  pid          TEXT,
  country      TEXT,
  token        TEXT,                       -- private reference for the optional second form step
  details_at   TEXT                        -- when the optional answers arrived
);
CREATE INDEX IF NOT EXISTS signups_ts ON signups (ts);
CREATE INDEX IF NOT EXISTS signups_token ON signups (token);
CREATE INDEX IF NOT EXISTS signups_email ON signups (email);

-- Migrations for databases created by an earlier version of this file:
--   ALTER TABLE signups ADD COLUMN payment_pref TEXT;
--   ALTER TABLE signups ADD COLUMN token TEXT;
--   ALTER TABLE signups ADD COLUMN details_at TEXT;
--   CREATE INDEX IF NOT EXISTS signups_token ON signups (token);
