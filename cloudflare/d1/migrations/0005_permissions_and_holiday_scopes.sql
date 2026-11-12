-- Cloudflare D1 migration 0005: Granular permissions and scoped holidays
ALTER TABLE auth_users ADD COLUMN permissions TEXT DEFAULT NULL;
ALTER TABLE holidays ADD COLUMN department TEXT DEFAULT 'All';
ALTER TABLE holidays ADD COLUMN employee_ids TEXT DEFAULT 'All';
