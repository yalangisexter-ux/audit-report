PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS chat_users (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 username TEXT NOT NULL COLLATE NOCASE UNIQUE,
 display_name TEXT NOT NULL DEFAULT '',
 role TEXT NOT NULL CHECK(role IN ('Admin','HR')),
 password_salt TEXT NOT NULL,
 password_hash TEXT NOT NULL,
 active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS conversations (
 id TEXT PRIMARY KEY,
 kind TEXT NOT NULL CHECK(kind IN ('private','group')),
 name TEXT NOT NULL DEFAULT '',
 direct_key TEXT UNIQUE,
 created_by INTEGER NOT NULL REFERENCES chat_users(id),
 created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS conversation_members (
 conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
 user_id INTEGER NOT NULL REFERENCES chat_users(id) ON DELETE CASCADE,
 member_role TEXT NOT NULL DEFAULT 'member' CHECK(member_role IN ('owner','member')),
 joined_at TEXT NOT NULL,
 PRIMARY KEY(conversation_id,user_id)
);
CREATE TABLE IF NOT EXISTS messages (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
 sender_user_id INTEGER NOT NULL REFERENCES chat_users(id),
 text TEXT NOT NULL CHECK(length(text) BETWEEN 1 AND 4000),
 created_at TEXT NOT NULL,
 client_message_id TEXT,
 UNIQUE(sender_user_id,client_message_id)
);
CREATE TABLE IF NOT EXISTS socket_tickets (
 ticket_hash TEXT PRIMARY KEY,
 user_id INTEGER NOT NULL REFERENCES chat_users(id) ON DELETE CASCADE,
 conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
 expires_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS login_attempts (
 attempt_key TEXT PRIMARY KEY,
 window_started INTEGER NOT NULL,
 attempts INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_members_user ON conversation_members(user_id,conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id,id DESC);
CREATE INDEX IF NOT EXISTS idx_tickets_expiry ON socket_tickets(expires_at);
