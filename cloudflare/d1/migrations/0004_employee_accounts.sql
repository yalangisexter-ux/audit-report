-- Cloudflare D1 migration 0004: Employee account mapping and task approval workflow
ALTER TABLE auth_users ADD COLUMN employee_id INTEGER DEFAULT NULL REFERENCES employees(id);
ALTER TABLE tasks ADD COLUMN approval_status TEXT DEFAULT 'Pending';
