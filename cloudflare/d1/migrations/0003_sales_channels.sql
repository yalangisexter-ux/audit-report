-- USA–Raw Strength multi-channel commerce integration (additive only).
CREATE TABLE IF NOT EXISTS sales_channels (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  platform TEXT NOT NULL CHECK(platform IN ('amazon_india','flipkart','meesho','shopify','woocommerce','etsy','ebay','other')),
  account_label TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending_authorization',
  auth_type TEXT NOT NULL,
  credentials_ciphertext TEXT NOT NULL DEFAULT '',
  webhook_secret_hash TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  last_sync_at TEXT,
  last_error TEXT
);
CREATE INDEX IF NOT EXISTS idx_sales_channels_platform_status ON sales_channels(platform,status);
CREATE TABLE IF NOT EXISTS marketplace_orders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  channel_id INTEGER NOT NULL REFERENCES sales_channels(id),
  external_order_id TEXT NOT NULL,
  external_status TEXT NOT NULL DEFAULT 'new',
  currency TEXT NOT NULL DEFAULT 'INR',
  total_amount REAL NOT NULL DEFAULT 0,
  customer_name TEXT NOT NULL DEFAULT '',
  customer_email TEXT NOT NULL DEFAULT '',
  customer_phone TEXT NOT NULL DEFAULT '',
  shipping_address TEXT NOT NULL DEFAULT '{}',
  ordered_at TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  last_event_id INTEGER,
  UNIQUE(channel_id, external_order_id)
);
CREATE INDEX IF NOT EXISTS idx_marketplace_orders_ordered_at ON marketplace_orders(ordered_at DESC);
CREATE TABLE IF NOT EXISTS marketplace_order_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  marketplace_order_id INTEGER NOT NULL REFERENCES marketplace_orders(id) ON DELETE CASCADE,
  external_item_id TEXT NOT NULL DEFAULT '',
  sku TEXT NOT NULL DEFAULT '',
  title TEXT NOT NULL,
  quantity INTEGER NOT NULL DEFAULT 1,
  unit_price REAL NOT NULL DEFAULT 0,
  currency TEXT NOT NULL DEFAULT 'INR',
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_marketplace_order_items_sku ON marketplace_order_items(sku);
CREATE TABLE IF NOT EXISTS marketplace_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  channel_id INTEGER NOT NULL REFERENCES sales_channels(id),
  external_event_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  processing_status TEXT NOT NULL DEFAULT 'received',
  received_at TEXT NOT NULL,
  UNIQUE(channel_id, external_event_id)
);
CREATE INDEX IF NOT EXISTS idx_marketplace_events_status ON marketplace_events(processing_status,received_at);
CREATE TABLE IF NOT EXISTS sales_sync_jobs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  channel_id INTEGER NOT NULL REFERENCES sales_channels(id),
  job_type TEXT NOT NULL,
  status TEXT NOT NULL,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  error_message TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS sales_notifications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  channel_id INTEGER REFERENCES sales_channels(id),
  notification_type TEXT NOT NULL,
  title TEXT NOT NULL,
  message TEXT NOT NULL,
  created_at TEXT NOT NULL,
  read_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_sales_notifications_created ON sales_notifications(created_at DESC);
CREATE TABLE IF NOT EXISTS channel_product_mappings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  channel_id INTEGER NOT NULL REFERENCES sales_channels(id),
  external_listing_id TEXT NOT NULL DEFAULT '',
  external_sku TEXT NOT NULL,
  product_id INTEGER NOT NULL REFERENCES bt_products(id),
  mapping_status TEXT NOT NULL DEFAULT 'pending_review',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(channel_id, external_sku)
);
CREATE INDEX IF NOT EXISTS idx_channel_product_mappings_product ON channel_product_mappings(product_id);
