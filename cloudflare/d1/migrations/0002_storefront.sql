-- USA–Raw Strength customer storefront and order capture.
-- Additive only: existing desktop inventory, employee data and authentication are untouched.
CREATE TABLE IF NOT EXISTS store_orders (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 order_code TEXT NOT NULL UNIQUE,
 customer_name TEXT NOT NULL,
 phone TEXT NOT NULL,
 email TEXT DEFAULT '',
 shipping_address TEXT NOT NULL,
 order_status TEXT NOT NULL DEFAULT 'Pending',
 payment_method TEXT NOT NULL DEFAULT 'Cash on Delivery',
 payment_status TEXT NOT NULL DEFAULT 'Unpaid',
 subtotal REAL NOT NULL DEFAULT 0,
 total_amount REAL NOT NULL DEFAULT 0,
 customer_note TEXT DEFAULT '',
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS store_order_items (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 order_id INTEGER NOT NULL,
 product_id INTEGER,
 product_name TEXT NOT NULL,
 sku TEXT DEFAULT '',
 quantity INTEGER NOT NULL CHECK(quantity > 0),
 unit TEXT DEFAULT 'PCS',
 unit_price REAL NOT NULL DEFAULT 0,
 line_total REAL NOT NULL DEFAULT 0,
 FOREIGN KEY(order_id) REFERENCES store_orders(id) ON DELETE CASCADE,
 FOREIGN KEY(product_id) REFERENCES bt_products(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_store_orders_created ON store_orders(created_at);
CREATE INDEX IF NOT EXISTS idx_store_orders_status ON store_orders(order_status);
CREATE INDEX IF NOT EXISTS idx_store_order_items_order ON store_order_items(order_id);
