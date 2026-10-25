"""Cloudflare-powered live chat tab for the Raw Strength desktop application.

Chat credentials are never persisted. Session tokens are stored only as Windows DPAPI-protected local settings so an existing session can reconnect without repeated sign-in. The existing local employee-audit login and SQLite business records are not sent to Cloudflare.
"""
from __future__ import annotations

import html
import json
import os
import re
import hashlib
import secrets
import threading
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from urllib.parse import urlsplit, urlunsplit

from database_sync import protect_sync_token, unprotect_sync_token

from PySide6.QtCore import Qt, QThread, QTimer, Signal, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QTextEdit, QInputDialog,
    QMessageBox, QFrame, QSizePolicy, QComboBox
)

_ACTIVE_REQUESTS = set()
_ACTIVE_SOCKETS = set()

# The release workflow injects the deployed Worker HTTPS URL at build time.
# Keep this empty in source control; never guess a production workers.dev hostname.
DEFAULT_CHAT_API_BASE = ""
FALLBACK_CHAT_API_BASE = "https://raw-strength-employee-chat.yalangisexter.workers.dev"

try:
    import websocket
except ImportError:  # The packaged build installs websocket-client from requirements.txt.
    websocket = None


def setup_chat_tables(conn):
    """Ensure local additive tables for offline/local chat exist."""
    conn.execute("""
    CREATE TABLE IF NOT EXISTS local_chat_conversations (
        id TEXT PRIMARY KEY,
        user_name TEXT NOT NULL,
        last_message TEXT DEFAULT '',
        updated_at TEXT NOT NULL
    )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS local_chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id TEXT NOT NULL,
        sender_role TEXT NOT NULL,
        sender_name TEXT NOT NULL,
        text TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)
    conn.commit()


def verify_developer_password(password: str) -> bool:
    """Verify developer password using PBKDF2 HMAC SHA-256 or authorized developer keys."""
    if not password:
        return False
    pwd = str(password).strip()
    # Do not accept extra hard-coded plaintext password aliases. Keep the
    # PBKDF2-backed legacy credential below for existing authorized workflows.
    if os.environ.get("DEVELOPER_PASSWORD") and secrets.compare_digest(pwd, os.environ["DEVELOPER_PASSWORD"].strip()):
        return True
    expected_primary = bytes.fromhex("a39b5cc22ca0d7b85e0f963439352d157e45ec125f2372077dfb8a459d2b33c6")
    expected_legacy = bytes.fromhex("c408585fbeeed010ea54f7fb51c80053546baec2b6831c1abfdc886777b330ec")
    actual = hashlib.pbkdf2_hmac(
        "sha256", pwd.encode("utf-8"), b"RSC-Pull-Latest-Data-v1", 300000
    )
    if secrets.compare_digest(actual, expected_primary) or secrets.compare_digest(actual, expected_legacy):
        return True
    return False


def normalize_api_base(value: str) -> str:
    """Validate and normalize a Cloudflare Worker HTTPS URL."""
    parsed = urlsplit(str(value or "").strip())
    if parsed.scheme not in ("https", "http") or not parsed.netloc:
        raise ValueError("Enter the HTTPS URL of the deployed Cloudflare Worker.")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("The chat service URL must not contain credentials, a query, or a fragment.")
    if parsed.path not in ("", "/"):
        raise ValueError("Enter only the Worker base URL, without an API path.")
    if parsed.scheme != "https" and parsed.hostname not in ("localhost", "127.0.0.1", "::1"):
        raise ValueError("Use HTTPS for the deployed chat service.")
    return urlunsplit((parsed.scheme, parsed.netloc, "", "", "")).rstrip("/")


def websocket_url(api_base: str, ticket: str) -> str:
    parsed = urlsplit(normalize_api_base(api_base))
    scheme = "wss" if parsed.scheme == "https" else "ws"
    query = urllib.parse.urlencode({"ticket": ticket})
    return urlunsplit((scheme, parsed.netloc, "/api/chat/ws", query, ""))


def _api_call(base: str, path: str, token: str, method: str, payload: dict | None):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {
        "Accept": "application/json",
        "Cache-Control": "no-store",
        "User-Agent": "RawStrengthEmployeeAuditManager/1.2 (Windows NT 10.0; Win64; x64)",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(base + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            raw = response.read(1024 * 1024)
            data = json.loads(raw.decode("utf-8") or "{}")
    except urllib.error.HTTPError as exc:
        try:
            data = json.loads(exc.read(65536).decode("utf-8") or "{}")
            message = str(data.get("error") or "Chat request failed (HTTP %s)." % exc.code)
        except Exception:
            message = "Chat request failed (HTTP %s)." % exc.code
        raise RuntimeError(message) from None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError("Could not reach the chat service. Check the Worker URL and internet connection.") from exc
    if not isinstance(data, dict):
        raise RuntimeError("The chat service returned an invalid response.")
    return data


class _ApiRequest(QThread):
    completed = Signal(str, object, str)

    def __init__(self, request_id: str, base: str, path: str, token: str = "", method: str = "GET", payload: dict | None = None):
        super().__init__()
        self.request_id = request_id
        self.base = base
        self.path = path
        self.token = token
        self.method = method
        self.payload = payload

    def run(self):
        try:
            data = _api_call(self.base, self.path, self.token, self.method, self.payload)
            if data.get("error"):
                raise RuntimeError(str(data["error"]))
            self.completed.emit(self.request_id, data, "")
        except Exception as exc:
            self.completed.emit(self.request_id, {}, str(exc))


class _ChatSocket(QThread):
    event_received = Signal(object)
    state_changed = Signal(str)

    def __init__(self, url: str):
        super().__init__()
        self.url = url
        self.app = None
        self._stop_requested = threading.Event()

    def run(self):
        if websocket is None:
            self.state_changed.emit("WebSocket support is not installed.")
            return

        def on_open(_app):
            self.state_changed.emit("Connected")

        def on_message(_app, raw):
            try:
                packet = json.loads(raw)
                if isinstance(packet, dict):
                    self.event_received.emit(packet)
            except Exception:
                self.state_changed.emit("Received an invalid chat event.")

        def on_error(_app, error):
            if not self._stop_requested.is_set():
                self.state_changed.emit("Connection error: " + str(error)[:160])

        def on_close(_app, _code, _reason):
            if not self._stop_requested.is_set():
                self.state_changed.emit("Disconnected")

        self.app = websocket.WebSocketApp(
            self.url, on_open=on_open, on_message=on_message,
            on_error=on_error, on_close=on_close,
        )
        try:
            self.app.run_forever(ping_interval=25, ping_timeout=10)
        except Exception as exc:
            if not self._stop_requested.is_set():
                self.state_changed.emit("Connection closed: " + str(exc)[:160])
        finally:
            if not self._stop_requested.is_set():
                self.state_changed.emit("Disconnected")

    def send_packet(self, packet: dict) -> bool:
        app = self.app
        if not app or not app.sock or not app.sock.connected:
            return False
        try:
            app.send(json.dumps(packet))
            return True
        except Exception:
            return False

    def stop(self):
        self._stop_requested.set()
        app = self.app
        if app:
            try:
                app.close()
            except Exception:
                pass


class CloudflareChatTab(QWidget):
    """Standalone real-time chat view embedded in the existing desktop sidebar."""

    def __init__(self, db, current_user: dict, parent=None):
        super().__init__(parent)
        self.db = db
        self.current_user = dict(current_user or {})
        if hasattr(self.db, "conn") and self.db.conn is not None:
            setup_chat_tables(self.db.conn)
        self.token = ""
        self.chat_user = None
        self.current_role = ""
        self.current_display_name = ""
        stored = str(self.db.get_setting("cloudflare_chat_api_url", "") or "")
        self.api_base = DEFAULT_CHAT_API_BASE or stored or FALLBACK_CHAT_API_BASE
        if DEFAULT_CHAT_API_BASE and stored != DEFAULT_CHAT_API_BASE:
            self.db.set_setting("cloudflare_chat_api_url", DEFAULT_CHAT_API_BASE)

        self.conversations = []
        self.users = []
        self.active_conversation = None
        self.messages = []
        self._workers = set()
        self._socket = None
        self._socket_generation = 0
        self._retry_count = 0
        self._reconnect_pending = False
        self._current_ticket_request = ""
        self._preferred_conversation_id = ""
        self._refresh_inflight = False
        self._build_ui()

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(1200)
        self._poll_timer.timeout.connect(self._poll_updates)
        self._poll_timer.start()

        self._conversation_refresh_timer = QTimer(self)
        self._conversation_refresh_timer.setInterval(15000)
        self._conversation_refresh_timer.timeout.connect(lambda: self._request("conversations", "/api/conversations") if self.token else None)
        if websocket is None and self.api_base:
            self.status_label.setText("Install websocket-client to enable cloud live delivery.")
            self.status_label.setStyleSheet("color:#b91c1c;")
        else:
            self._restore_session()

    def _restore_session(self):
        """Reconnect using the current Windows user's protected saved chat session."""
        if not self.api_base:
            return
        try:
            protected = str(self.db.get_setting("cloudflare_chat_session", "") or "")
            if not protected:
                return
            self.token = unprotect_sync_token(protected)
            self.login_panel.hide()
            self.chat_panel.show()
            self.status_label.setText("Reconnecting to Live Chat…")
            self._conversation_refresh_timer.start()
            self._request("session", "/api/users")
            self._request("conversations", "/api/conversations")
        except Exception:
            self.token = ""
            self.db.set_setting("cloudflare_chat_session", "")
            self.status_label.setText("Chat session expired · sign in once to reconnect")

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 12, 18, 14)
        root.setSpacing(10)

        top_bar = QHBoxLayout()
        self.role_badge = QLabel("Mode: Sign In Required")
        self.role_badge.setStyleSheet("font-size:12px;font-weight:700;color:#4338ca;")
        top_bar.addWidget(self.role_badge)
        top_bar.addStretch(1)
        self.status_label = QLabel("Not connected")
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.status_label.setStyleSheet("color:#64748b;font-size:12px;")
        top_bar.addWidget(self.status_label)
        root.addLayout(top_bar)

        self.login_panel = QFrame()
        self.login_panel.setObjectName("chatLoginPanel")
        self.login_panel.setStyleSheet(
            "#chatLoginPanel{background:rgba(255,255,255,230);border:1px solid #ddd6fe;border-radius:14px;}"
        )
        login_layout = QVBoxLayout(self.login_panel)
        login_layout.setContentsMargins(20, 18, 20, 18)
        login_layout.setSpacing(12)

        role_row = QHBoxLayout()
        role_label = QLabel("Select Role:")
        role_label.setStyleSheet("font-weight:700;color:#312e81;")
        self.role_combo = QComboBox()
        self.role_combo.addItems(["User (Customer)", "Support (Developer Authorization)"])
        self.role_combo.setMinimumHeight(34)
        self.role_combo.currentIndexChanged.connect(self._on_role_changed)
        role_row.addWidget(role_label)
        role_row.addWidget(self.role_combo, 1)
        login_layout.addLayout(role_row)

        self.role_info_label = QLabel("Customers text support directly without a password. Enter your name below.")
        self.role_info_label.setWordWrap(True)
        self.role_info_label.setStyleSheet("color:#475569;font-size:12px;")
        login_layout.addWidget(self.role_info_label)

        form = QFormLayout()
        form.setSpacing(10)
        self.user_name_edit = QLineEdit()
        self.user_name_edit.setPlaceholderText("Enter your name (shown to support)")
        self.user_name_edit.setMinimumHeight(34)
        default_user = str(self.current_user.get("display_name") or self.current_user.get("username") or "")
        if default_user:
            self.user_name_edit.setText(default_user)
        self.user_name_edit.returnPressed.connect(self._handle_connect)
        self.username_edit = self.user_name_edit  # Compatibility alias
        self.name_row_label = QLabel("Your Name")
        form.addRow(self.name_row_label, self.user_name_edit)

        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("Enter developer password")
        self.password_edit.setMinimumHeight(34)
        self.password_edit.returnPressed.connect(self._handle_connect)
        self.pwd_row_label = QLabel("Developer Password")
        form.addRow(self.pwd_row_label, self.password_edit)
        login_layout.addLayout(form)

        # User mode is active by default; hide developer password
        self.pwd_row_label.hide()
        self.password_edit.hide()

        self.login_error = QLabel("")
        self.login_error.setWordWrap(True)
        self.login_error.setStyleSheet("color:#b91c1c;font-weight:600;")
        login_layout.addWidget(self.login_error)

        login_buttons = QHBoxLayout()
        login_buttons.addStretch(1)
        self.login_button = QPushButton("Start Chat as User")
        self.login_button.setMinimumHeight(38)
        self.login_button.setStyleSheet(
            "QPushButton{background:#6d28d9;color:white;border:0;border-radius:9px;padding:8px 20px;font-weight:700;} "
            "QPushButton:hover{background:#5b21b6;}"
        )
        self.login_button.clicked.connect(self._handle_connect)
        login_buttons.addWidget(self.login_button)
        login_layout.addLayout(login_buttons)
        root.addWidget(self.login_panel)

        self.chat_panel = QFrame()
        self.chat_panel.setObjectName("chatMainPanel")
        self.chat_panel.setStyleSheet(
            "#chatMainPanel{background:rgba(255,255,255,230);border:1px solid #ddd6fe;border-radius:14px;}"
        )
        chat_layout = QHBoxLayout(self.chat_panel)
        chat_layout.setContentsMargins(12, 12, 12, 12)
        chat_layout.setSpacing(12)

        left = QVBoxLayout()
        left.setSpacing(8)
        self.conv_list_heading = QLabel("Conversations")
        self.conv_list_heading.setStyleSheet("font-weight:700;color:#1e1b4b;font-size:13px;")
        left.addWidget(self.conv_list_heading)

        self.conversation_list = QListWidget()
        self.conversation_list.setMinimumWidth(210)
        self.conversation_list.setMaximumWidth(310)
        self.conversation_list.setStyleSheet(
            "QListWidget{background:rgba(248,250,252,240);color:#0f172a;border:1px solid #e2e8f0;border-radius:10px;padding:4px;} "
            "QListWidget::item{padding:9px;border-radius:7px;} "
            "QListWidget::item:selected{background:#ddd6fe;color:#312e81;font-weight:600;}"
        )
        self.conversation_list.currentItemChanged.connect(self._select_conversation)
        left.addWidget(self.conversation_list, 1)

        self.user_mode_info = QLabel("")
        self.user_mode_info.setWordWrap(True)
        self.user_mode_info.setStyleSheet("color:#475569;font-size:11px;padding:4px;")
        left.addWidget(self.user_mode_info)

        self.logout_button = QPushButton("Sign out / Switch Role")
        self.logout_button.setStyleSheet(
            "QPushButton{background:#f1f5f9;color:#334155;border:1px solid #cbd5e1;border-radius:8px;padding:7px;} "
            "QPushButton:hover{background:#e2e8f0;}"
        )
        self.logout_button.clicked.connect(self._logout)
        left.addWidget(self.logout_button)

        # Hidden controls for compatibility
        self.private_button = QPushButton("+ Private")
        self.group_button = QPushButton("+ Group")
        self.admin_button = QPushButton("Add account")
        self.add_member_button = QPushButton("Add member")
        self.change_password_button = QPushButton("Change password")
        for btn in (self.private_button, self.group_button, self.admin_button, self.add_member_button, self.change_password_button):
            btn.hide()

        right = QVBoxLayout()
        right.setSpacing(8)
        heading_actions = QHBoxLayout()
        self.conversation_heading = QLabel("Conversation")
        self.conversation_heading.setStyleSheet("font-size:15px;font-weight:700;color:#1e1b4b;")
        heading_actions.addWidget(self.conversation_heading, 1)

        self.screen_share_button = QPushButton("▣ Screen share & control")
        self.screen_share_button.setToolTip(
            "Open the secure browser chat. Sign in, open the conversation, then use Share screen."
        )
        self.screen_share_button.setMinimumHeight(32)
        self.screen_share_button.setStyleSheet(
            "QPushButton{background:#0f766e;color:white;border:0;border-radius:8px;padding:5px 10px;font-weight:600;font-size:11px;} "
            "QPushButton:hover{background:#115e59;}"
        )
        self.screen_share_button.clicked.connect(self._open_screen_share_browser)
        heading_actions.addWidget(self.screen_share_button)
        right.addLayout(heading_actions)

        self.history = QTextEdit()
        self.history.setReadOnly(True)
        self.history.setAcceptRichText(False)
        self.history.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.history.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self.history.setStyleSheet(
            "QTextEdit { background: rgba(248,250,252,245); color: #0f172a; border: 1px solid #e2e8f0; border-radius: 10px; padding: 10px; selection-background-color: transparent; } "
            "QTextEdit:focus { border: 1px solid #cbd5e1; outline: none; }"
        )
        right.addWidget(self.history, 1)

        composer = QHBoxLayout()
        self.message_edit = QLineEdit()
        self.message_edit.setPlaceholderText("Write a message…")
        self.message_edit.setMaxLength(4000)
        self.message_edit.setMinimumHeight(38)
        self.message_edit.returnPressed.connect(self._send_message)
        self.send_button = QPushButton("Send")
        self.send_button.setMinimumWidth(86)
        self.send_button.setMinimumHeight(38)
        self.send_button.setStyleSheet(
            "QPushButton{background:#6d28d9;color:white;border:0;border-radius:9px;padding:8px 14px;font-weight:700;} "
            "QPushButton:hover{background:#5b21b6;}"
        )
        self.send_button.clicked.connect(self._send_message)
        composer.addWidget(self.message_edit, 1)
        composer.addWidget(self.send_button)
        right.addLayout(composer)

        chat_layout.addLayout(left)
        right_frame = QFrame()
        right_frame.setLayout(right)
        chat_layout.addWidget(right_frame, 1)
        root.addWidget(self.chat_panel, 1)
        self.chat_panel.hide()
        self.apply_theme()

    def apply_theme(self, theme_name=None):
        if not theme_name and hasattr(self, "db") and hasattr(self.db, "get_setting"):
            try:
                theme_name = self.db.get_setting("ui_theme", "day")
            except Exception:
                theme_name = "day"
        theme = (theme_name or "day").lower()
        if theme in ("night", "dark"):
            card_bg = "rgba(15, 23, 42, 0.95)"
            card_border = "#334155"
            text_color = "#F8FAFC"
            muted_color = "#94A3B8"
            input_bg = "#0B1120"
            input_border = "#334155"
            list_bg = "rgba(11, 17, 32, 0.95)"
            list_border = "#1E293B"
            list_item_sel_bg = "#4C1D95"
            list_item_sel_fg = "#FFFFFF"
            history_bg = "rgba(11, 17, 32, 0.95)"
            history_border = "#334155"
            role_label_color = "#C4B5FD"
            role_badge_bg = "#312E81"
            role_badge_fg = "#DDD6FE"
            btn_bg = "#7C3AED"
            btn_hover = "#6D28D9"
            btn_fg = "#FFFFFF"
            btn_sec_bg = "#1E293B"
            btn_sec_fg = "#E2E8F0"
            btn_sec_border = "#334155"
        elif theme == "ocean":
            card_bg = "rgba(240, 249, 255, 0.95)"
            card_border = "#BAE6FD"
            text_color = "#0C4A6E"
            muted_color = "#0369A1"
            input_bg = "#FFFFFF"
            input_border = "#BAE6FD"
            list_bg = "rgba(224, 242, 254, 0.95)"
            list_border = "#BAE6FD"
            list_item_sel_bg = "#0284C7"
            list_item_sel_fg = "#FFFFFF"
            history_bg = "#FFFFFF"
            history_border = "#BAE6FD"
            role_label_color = "#0369A1"
            role_badge_bg = "#E0F2FE"
            role_badge_fg = "#0369A1"
            btn_bg = "#0284C7"
            btn_hover = "#0369A1"
            btn_fg = "#FFFFFF"
            btn_sec_bg = "#E0F2FE"
            btn_sec_fg = "#0C4A6E"
            btn_sec_border = "#BAE6FD"
        elif theme == "sunset":
            card_bg = "rgba(255, 247, 237, 0.95)"
            card_border = "#FED7AA"
            text_color = "#7C2D12"
            muted_color = "#C2410C"
            input_bg = "#FFFFFF"
            input_border = "#FED7AA"
            list_bg = "rgba(255, 237, 213, 0.95)"
            list_border = "#FED7AA"
            list_item_sel_bg = "#EA580C"
            list_item_sel_fg = "#FFFFFF"
            history_bg = "#FFFFFF"
            history_border = "#FED7AA"
            role_label_color = "#9A3412"
            role_badge_bg = "#FFEDD5"
            role_badge_fg = "#9A3412"
            btn_bg = "#EA580C"
            btn_hover = "#C2410C"
            btn_fg = "#FFFFFF"
            btn_sec_bg = "#FFEDD5"
            btn_sec_fg = "#7C2D12"
            btn_sec_border = "#FED7AA"
        else:  # Day
            card_bg = "rgba(255, 255, 255, 0.96)"
            card_border = "#CBD5E1"
            text_color = "#0F172A"
            muted_color = "#64748B"
            input_bg = "#FFFFFF"
            input_border = "#CBD5E1"
            list_bg = "rgba(248, 250, 252, 0.95)"
            list_border = "#E2E8F0"
            list_item_sel_bg = "#DDD6FE"
            list_item_sel_fg = "#312E81"
            history_bg = "#FFFFFF"
            history_border = "#E2E8F0"
            role_label_color = "#312E81"
            role_badge_bg = "#EDE9FE"
            role_badge_fg = "#4C1D95"
            btn_bg = "#6D28D9"
            btn_hover = "#5B21B6"
            btn_fg = "#FFFFFF"
            btn_sec_bg = "#F1F5F9"
            btn_sec_fg = "#334155"
            btn_sec_border = "#CBD5E1"

        if hasattr(self, "login_panel"):
            self.login_panel.setStyleSheet(f"#chatLoginPanel {{ background: {card_bg}; border: 1.5px solid {card_border}; border-radius: 16px; }}")
        if hasattr(self, "chat_panel"):
            self.chat_panel.setStyleSheet(f"#chatMainPanel {{ background: {card_bg}; border: 1.5px solid {card_border}; border-radius: 16px; }}")
        if hasattr(self, "conversation_list"):
            self.conversation_list.setStyleSheet(f"""
                QListWidget {{ background: {list_bg}; color: {text_color}; border: 1.5px solid {list_border}; border-radius: 10px; padding: 6px; }}
                QListWidget::item {{ padding: 9px; border-radius: 7px; color: {text_color}; }}
                QListWidget::item:selected {{ background: {list_item_sel_bg}; color: {list_item_sel_fg}; font-weight: 700; }}
            """)
        if hasattr(self, "history"):
            self.history.setStyleSheet(f"""
                QTextEdit {{ background: {history_bg}; color: {text_color}; border: 1.5px solid {history_border}; border-radius: 10px; padding: 12px; selection-background-color: transparent; }}
                QTextEdit:focus {{ border-color: {card_border}; outline: none; }}
            """)
        if hasattr(self, "message_edit"):
            self.message_edit.setStyleSheet(f"""
                QLineEdit {{ background: {input_bg}; color: {text_color}; border: 1.5px solid {input_border}; border-radius: 9px; padding: 6px 12px; }}
                QLineEdit:focus {{ border-color: {btn_bg}; }}
            """)
        if hasattr(self, "user_name_edit"):
            self.user_name_edit.setStyleSheet(f"""
                QLineEdit {{ background: {input_bg}; color: {text_color}; border: 1.5px solid {input_border}; border-radius: 9px; padding: 6px 12px; }}
                QLineEdit:focus {{ border-color: {btn_bg}; }}
            """)
        if hasattr(self, "password_edit"):
            self.password_edit.setStyleSheet(f"""
                QLineEdit {{ background: {input_bg}; color: {text_color}; border: 1.5px solid {input_border}; border-radius: 9px; padding: 6px 12px; }}
                QLineEdit:focus {{ border-color: {btn_bg}; }}
            """)
        if hasattr(self, "send_button"):
            self.send_button.setStyleSheet(f"""
                QPushButton {{ background: {btn_bg}; color: {btn_fg}; border: 0; border-radius: 9px; padding: 8px 16px; font-weight: 700; }}
                QPushButton:hover {{ background: {btn_hover}; }}
            """)
        if hasattr(self, "login_button"):
            self.login_button.setStyleSheet(f"""
                QPushButton {{ background: {btn_bg}; color: {btn_fg}; border: 0; border-radius: 9px; padding: 8px 20px; font-weight: 700; }}
                QPushButton:hover {{ background: {btn_hover}; }}
            """)
        if hasattr(self, "logout_button"):
            self.logout_button.setStyleSheet(f"""
                QPushButton {{ background: {btn_sec_bg}; color: {btn_sec_fg}; border: 1px solid {btn_sec_border}; border-radius: 8px; padding: 7px; font-weight: 600; }}
                QPushButton:hover {{ background: {input_border}; }}
            """)
        if hasattr(self, "conv_list_heading"):
            self.conv_list_heading.setStyleSheet(f"font-weight: 700; color: {text_color}; font-size: 13px;")
        if hasattr(self, "conversation_heading"):
            self.conversation_heading.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {text_color};")
        if hasattr(self, "status_label"):
            self.status_label.setStyleSheet(f"color: {muted_color}; font-size: 12px;")
        if hasattr(self, "role_info_label"):
            self.role_info_label.setStyleSheet(f"color: {muted_color}; font-size: 12px;")
        if hasattr(self, "role_badge"):
            self.role_badge.setStyleSheet(f"background: {role_badge_bg}; color: {role_badge_fg}; font-size: 12px; font-weight: 700; border-radius: 8px; padding: 4px 10px;")
        if hasattr(self, "messages") and self.messages:
            self._render_messages()

    def _on_role_changed(self, index):
        self.login_error.clear()
        if index == 0:  # User (Customer)
            self.pwd_row_label.hide()
            self.password_edit.hide()
            self.name_row_label.show()
            self.user_name_edit.show()
            self.login_button.setText("Start Chat as User")
            self.role_info_label.setText("Customers text support directly without a password. Enter your name below.")
        else:  # Support (Developer Authorization)
            self.pwd_row_label.show()
            self.password_edit.show()
            self.name_row_label.hide()
            self.user_name_edit.hide()
            self.login_button.setText("Sign in as Support")
            self.role_info_label.setText("Support mode requires developer password authorization. You can receive all users' messages and switch conversations.")

    def _login(self):
        """Compatibility alias for connect button / Enter key."""
        self._handle_connect()

    def _handle_connect(self):
        self.login_error.clear()
        role_idx = self.role_combo.currentIndex()
        if role_idx == 0:  # User
            name = self.user_name_edit.text().strip()
            if not name:
                self.login_error.setText("Please enter your name so support knows who is texting.")
                return
            self._connect_as_user(name)
        else:  # Support
            pwd = self.password_edit.text()
            if not pwd:
                self.login_error.setText("Enter the developer password.")
                return
            if not verify_developer_password(pwd):
                self.login_error.setText("Developer authorization failed. Incorrect developer password.")
                return
            self._connect_as_support()

    def _connect_as_user(self, name):
        self.current_role = "User"
        self.current_display_name = name
        safe_id = "user_" + re.sub(r"[^a-zA-Z0-9_]", "_", name.strip().lower())
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if hasattr(self.db, "conn") and self.db.conn is not None:
            cur = self.db.conn.cursor()
            cur.execute("SELECT id FROM local_chat_conversations WHERE id=?", (safe_id,))
            if not cur.fetchone():
                self.db.conn.execute(
                    "INSERT INTO local_chat_conversations (id, user_name, last_message, updated_at) VALUES (?, ?, ?, ?)",
                    (safe_id, name, "", now_str)
                )
                self.db.conn.commit()

        self.active_conversation = {"id": safe_id, "user_name": name, "title": f"Support Team ({name})"}
        self.login_panel.hide()
        self.chat_panel.show()
        self.role_badge.setText(f"Mode: User ({name})")
        self.status_label.setText(f"Connected as {name}")
        self.conv_list_heading.setText("Support Contact")
        self.conversation_heading.setText("Support Team")
        self.user_mode_info.setText(f"You are texting Support as:\n{name}")
        self.user_mode_info.show()

        self.conversation_list.blockSignals(True)
        self.conversation_list.clear()
        item = QListWidgetItem("Support Team\nDirect support channel")
        item.setData(Qt.ItemDataRole.UserRole, self.active_conversation)
        self.conversation_list.addItem(item)
        self.conversation_list.setCurrentItem(item)
        self.conversation_list.blockSignals(False)

        self.message_edit.setEnabled(True)
        self.send_button.setEnabled(True)
        self._reload_messages()

    def _connect_as_support(self):
        self.current_role = "Support"
        self.current_display_name = "Support"
        self.login_panel.hide()
        self.chat_panel.show()
        self.role_badge.setText("Mode: Support · Developer Authorized")
        self.status_label.setText("Support Mode (All user conversations)")
        self.conv_list_heading.setText("All User Conversations")
        self.user_mode_info.hide()

        self._reload_conversations()
        if self.conversations:
            self._open_conversation(self.conversations[0])
        else:
            self.active_conversation = None
            self.history.clear()
            self.conversation_heading.setText("No user conversations yet")
            self.history.setHtml("<p style='color:#64748b;padding:12px;'>No users have sent a message yet. When a user sends a message, their conversation will appear here.</p>")
            self.message_edit.setEnabled(False)
            self.send_button.setEnabled(False)

    def _reload_conversations(self):
        if not hasattr(self.db, "conn") or self.db.conn is None:
            return
        cur = self.db.conn.cursor()
        cur.execute("SELECT id, user_name, last_message, updated_at FROM local_chat_conversations ORDER BY updated_at DESC")
        rows = cur.fetchall()
        self.conversations = []
        for row in rows:
            self.conversations.append({
                "id": str(row[0]),
                "user_name": str(row[1]),
                "title": f"Chat with {row[1]}",
                "last_message": str(row[2] or ""),
                "updated_at": str(row[3] or "")
            })
        self._render_conversations()

    def _render_conversations(self):
        if self.current_role != "Support":
            return
        selected_id = self.active_conversation.get("id") if self.active_conversation else ""
        self.conversation_list.blockSignals(True)
        self.conversation_list.clear()
        selected_item = None
        for conversation in self.conversations:
            title = str(conversation.get("user_name") or "Customer")
            preview = str(conversation.get("last_message") or "No messages yet")
            stamp = str(conversation.get("updated_at") or "")
            stamp_display = f" · {stamp[11:16]}" if len(stamp) >= 16 else ""
            item = QListWidgetItem(f"{title}{stamp_display}\n{preview[:60]}")
            item.setData(Qt.ItemDataRole.UserRole, conversation)
            item.setToolTip(f"{title}\n{preview}")
            self.conversation_list.addItem(item)
            if conversation.get("id") == selected_id:
                selected_item = item
        if selected_item is not None:
            self.conversation_list.setCurrentItem(selected_item)
        elif self.conversations and not self.active_conversation:
            self.conversation_list.setCurrentRow(0)
            self.active_conversation = self.conversations[0]
        self.conversation_list.blockSignals(False)

    def _select_conversation(self, current, _previous=None):
        if not current:
            return
        conversation = current.data(Qt.ItemDataRole.UserRole)
        if conversation:
            self._open_conversation(conversation)

    def _open_conversation(self, conversation):
        if not conversation:
            return
        self.active_conversation = conversation
        user_name = str(conversation.get("user_name") or conversation.get("name") or "User")
        if self.current_role == "Support":
            self.conversation_heading.setText(f"Chat with {user_name}")
        else:
            self.conversation_heading.setText("Support Team")
        self.message_edit.setEnabled(True)
        self.send_button.setEnabled(True)
        self._reload_messages()

    def _reload_messages(self):
        if not self.active_conversation or not hasattr(self.db, "conn") or self.db.conn is None:
            return
        conv_id = str(self.active_conversation["id"])
        cur = self.db.conn.cursor()
        cur.execute(
            "SELECT id, conversation_id, sender_role, sender_name, text, created_at FROM local_chat_messages WHERE conversation_id=? ORDER BY id ASC",
            (conv_id,)
        )
        rows = cur.fetchall()
        self.messages = []
        for row in rows:
            self.messages.append({
                "id": int(row[0]),
                "conversation_id": str(row[1]),
                "sender_role": str(row[2]),
                "sender_name": str(row[3]),
                "text": str(row[4]),
                "created_at": str(row[5]),
            })
        self._render_messages()

    def _remote_sync_conversations(self):
        base = self._base()
        if not base or getattr(self, "_syncing_remote_convs", False):
            return
        self._syncing_remote_convs = True

        def _worker():
            try:
                res = _api_call(base, "/api/support/conversations", "", "GET", None)
                convs = res.get("conversations", [])
                QTimer.singleShot(0, lambda: self._apply_remote_conversations(convs))
            except Exception:
                pass
            finally:
                self._syncing_remote_convs = False

        threading.Thread(target=_worker, name="chat-conv-sync", daemon=True).start()

    def _apply_remote_conversations(self, convs):
        if not convs or not hasattr(self.db, "conn") or self.db.conn is None:
            return
        updated = False
        cur = self.db.conn.cursor()
        for c in convs:
            cid = str(c.get("id") or "")
            uname = str(c.get("user_name") or "Customer")
            lmsg = str(c.get("last_message") or "")
            uat = str(c.get("updated_at") or "")
            if cid:
                cur.execute("SELECT last_message, updated_at FROM local_chat_conversations WHERE id=?", (cid,))
                existing = cur.fetchone()
                if not existing or existing[0] != lmsg or existing[1] != uat:
                    self.db.conn.execute(
                        "INSERT INTO local_chat_conversations(id, user_name, last_message, updated_at) "
                        "VALUES(?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET "
                        "user_name=excluded.user_name, last_message=excluded.last_message, updated_at=excluded.updated_at",
                        (cid, uname, lmsg, uat)
                    )
                    updated = True
        if updated:
            self.db.conn.commit()
            if self.current_role == "Support":
                self._reload_conversations()

    def _remote_sync_messages(self, conv_id: str):
        base = self._base()
        if not base or not conv_id or getattr(self, "_syncing_remote_msgs", False):
            return
        self._syncing_remote_msgs = True

        max_id = 0
        if hasattr(self.db, "conn") and self.db.conn is not None:
            cur = self.db.conn.cursor()
            cur.execute("SELECT COALESCE(MAX(id), 0) FROM local_chat_messages WHERE conversation_id=?", (conv_id,))
            row = cur.fetchone()
            if row:
                max_id = row[0]

        def _worker(cid=conv_id, after=max_id):
            try:
                path = f"/api/support/messages?conversation_id={urllib.parse.quote(cid)}"
                if after > 0:
                    path += f"&after={after}"
                res = _api_call(base, path, "", "GET", None)
                msgs = res.get("messages", [])
                QTimer.singleShot(0, lambda: self._apply_remote_messages(cid, msgs))
            except Exception:
                pass
            finally:
                self._syncing_remote_msgs = False

        threading.Thread(target=_worker, name="chat-msg-sync", daemon=True).start()

    def _apply_remote_messages(self, conv_id, msgs):
        if not msgs or not hasattr(self.db, "conn") or self.db.conn is None:
            return
        inserted = False
        cur = self.db.conn.cursor()
        for m in msgs:
            srole = str(m.get("sender_role") or "User")
            sname = str(m.get("sender_name") or srole)
            txt = str(m.get("text") or "")
            cat = str(m.get("created_at") or "")
            cur.execute(
                "SELECT 1 FROM local_chat_messages WHERE conversation_id=? AND text=? AND sender_role=? AND created_at=?",
                (conv_id, txt, srole, cat)
            )
            if not cur.fetchone():
                self.db.conn.execute(
                    "INSERT INTO local_chat_messages (conversation_id, sender_role, sender_name, text, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (conv_id, srole, sname, txt, cat)
                )
                inserted = True
        if inserted:
            self.db.conn.commit()
            if self.active_conversation and str(self.active_conversation.get("id")) == str(conv_id):
                self._reload_messages()

    def _poll_updates(self):
        if not self.chat_panel.isVisible():
            return
        if not hasattr(self.db, "conn") or self.db.conn is None:
            return
        if self.current_role == "Support":
            cur = self.db.conn.cursor()
            cur.execute("SELECT id, user_name, last_message, updated_at FROM local_chat_conversations ORDER BY updated_at DESC")
            rows = cur.fetchall()
            new_convs = [
                {"id": str(r[0]), "user_name": str(r[1]), "title": f"Chat with {r[1]}", "last_message": str(r[2] or ""), "updated_at": str(r[3] or "")}
                for r in rows
            ]
            if new_convs != self.conversations:
                self.conversations = new_convs
                self._render_conversations()
            self._remote_sync_conversations()
            if self.active_conversation:
                self._remote_sync_messages(str(self.active_conversation["id"]))
            self._poll_active_messages()
        elif self.current_role == "User":
            if self.active_conversation:
                self._remote_sync_messages(str(self.active_conversation["id"]))
            self._poll_active_messages()

    def _poll_active_messages(self):
        if not self.active_conversation or not hasattr(self.db, "conn") or self.db.conn is None:
            return
        conv_id = str(self.active_conversation["id"])
        cur = self.db.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM local_chat_messages WHERE conversation_id=?", (conv_id,))
        count = cur.fetchone()[0]
        if count != len(self.messages):
            self._reload_messages()

    def _open_screen_share_browser(self):
        """Open the responsive browser client for WebRTC screen sharing."""
        base = self.api_base or self._base()
        if not base:
            QMessageBox.warning(self, "Screen sharing", "Live Chat is not configured for this release. Contact the application administrator.")
            return
        if QDesktopServices.openUrl(QUrl(base)):
            QMessageBox.information(
                self, "Screen sharing",
                "The browser chat is opening. Sign in with your chat account, open the same conversation, "
                "then use Share screen. The browser will ask you to choose what to share."
            )
        else:
            QMessageBox.warning(self, "Screen sharing", "Could not open your default browser. Open this URL manually:\n" + base)

    def _base(self):
        """Use the centrally configured release endpoint; never ask customers for a URL."""
        candidate = self.api_base or DEFAULT_CHAT_API_BASE or FALLBACK_CHAT_API_BASE
        if not candidate:
            self.login_error.setText("Live Chat is not configured in this release. Contact the application administrator.")
            return ""
        try:
            base = normalize_api_base(candidate)
            self.api_base = base
            # Keep existing saved settings compatible, but prefer the centrally configured URL.
            if self.db.get_setting("cloudflare_chat_api_url", "") != base:
                self.db.set_setting("cloudflare_chat_api_url", base)
            self.login_error.setText("")
            return base
        except ValueError as exc:
            self.login_error.setText("Live Chat endpoint configuration is invalid. Contact the application administrator.")
            return ""

    def _request(self, request_id, path, method="GET", payload=None, token=None):
        base = self.api_base or self._base()
        if not base:
            return
        if request_id == "conversations":
            if self._refresh_inflight:
                return
            self._refresh_inflight = True
        worker = _ApiRequest(request_id, base, path, self.token if token is None else token, method, payload)
        self._workers.add(worker)
        _ACTIVE_REQUESTS.add(worker)
        worker.completed.connect(self._on_api_result)
        worker.finished.connect(lambda w=worker: self._cleanup_worker(w))
        worker.finished.connect(lambda w=worker: _ACTIVE_REQUESTS.discard(w))
        worker.start()

    def _cleanup_worker(self, worker):
        self._workers.discard(worker)
        worker.deleteLater()

    def _login(self):
        base = self._base()
        if not base:
            return
        if websocket is None:
            self.login_error.setText("Live WebSocket support is unavailable. Install the app's websocket-client dependency.")
            return
        username = self.username_edit.text().strip()
        password = self.password_edit.text()
        if not username or not password:
            self.login_error.setText("Enter your chat username and password.")
            return
        self.login_button.setEnabled(False)
        self.login_button.setText("Signing in…")
        self._request("login", "/api/auth/login", "POST", {"username": username, "password": password}, token="")

    def _on_api_result(self, request_id, data, error):
        if request_id == "session":
            if error:
                if "sign in" in error.lower() or "401" in error:
                    self._logout()
                    self.status_label.setText("Chat session expired · sign in once to reconnect")
                else:
                    self.status_label.setText(error)
                return
            self.users = data.get("users") or []
            self.chat_user = data.get("user") or {}
            self.admin_button.setVisible(self.chat_user.get("role") == "Admin")
            self.status_label.setText("Connected as %s" % (self.chat_user.get("displayName") or self.chat_user.get("username") or "employee"))
            return
        if request_id == "login":
            self.login_button.setEnabled(True)
            self.login_button.setText("Sign in to Live Chat")
            self.password_edit.clear()
            if error:
                self.login_error.setText(error)
                self.status_label.setText("Sign-in failed")
                return
            self.token = str(data.get("token") or "")
            self.chat_user = data.get("user") or {}
            if self.token:
                try:
                    self.db.set_setting("cloudflare_chat_session", protect_sync_token(self.token))
                except Exception:
                    pass
            if not self.token or not self.chat_user.get("id"):
                self.login_error.setText("The chat service returned an invalid session.")
                self.token = ""
                return
            self.login_panel.hide()
            self.chat_panel.show()
            self._conversation_refresh_timer.start()
            self.admin_button.setVisible(self.chat_user.get("role") == "Admin")
            self.status_label.setText("Signed in as %s" % (self.chat_user.get("displayName") or self.chat_user.get("username") or "employee"))
            self._request("users", "/api/users")
            self._request("conversations", "/api/conversations")
            return
        if request_id == "users":
            if not error:
                self.users = data.get("users") or []
            return
        if request_id == "conversations":
            self._refresh_inflight = False
            if error:
                self.status_label.setText(error)
                return
            self.conversations = data.get("conversations") or []
            self._render_conversations()
            desired = self._preferred_conversation_id or (self.active_conversation.get("id") if self.active_conversation else None)
            target = next((c for c in self.conversations if c.get("id") == desired), None)
            if target is None and self.conversations:
                target = self.conversations[0]
            self._preferred_conversation_id = ""
            if target:
                self._open_conversation(target)
            else:
                self.active_conversation = None
                self.history.clear()
                self.conversation_heading.setText("No conversations yet")
                self.status_label.setText("Start a private chat or create a group.")
            return
        if request_id.startswith("history:"):
            conversation_id = request_id.split(":", 1)[1]
            if error:
                self.status_label.setText(error)
                return
            if not self.active_conversation or self.active_conversation.get("id") != conversation_id:
                return
            for item in (data.get("messages") or []):
                self.messages[int(item["id"])] = item
            self._render_messages()
            return
        if request_id.startswith("ticket:"):
            conversation_id = request_id.split(":", 1)[1]
            if error:
                self.status_label.setText(error)
                if "Sign in" in error or "sign in" in error.lower():
                    self._logout()
                else:
                    self._schedule_reconnect(conversation_id)
                return
            if not self.active_conversation or self.active_conversation.get("id") != conversation_id:
                return
            self._start_socket(conversation_id, str(data.get("ticket") or ""))
            return
        if request_id in ("private", "group"):
            if error:
                self.status_label.setText(error)
                QMessageBox.warning(self, "Live Chat", error)
                return
            self._preferred_conversation_id = str(data.get("conversationId") or "")
            self._request("conversations", "/api/conversations")
            return
        if request_id == "change-password":
            if error:
                QMessageBox.warning(self, "Change chat password", error)
            else:
                QMessageBox.information(self, "Change chat password", "Your chat password has been changed.")
            return
        if request_id == "create-user":
            if error:
                QMessageBox.warning(self, "Create chat account", error)
            else:
                QMessageBox.information(self, "Create chat account", "Chat account created. Share its temporary password securely.")
                self._request("users", "/api/users")
            return
        if request_id == "add-member":
            if error:
                QMessageBox.warning(self, "Add group member", error)
            else:
                QMessageBox.information(self, "Live Chat", "Member added to the group.")
            return

    def _close_socket(self):
        self._socket_generation += 1
        self._reconnect_pending = False
        worker = self._socket
        self._socket = None
        if worker is not None:
            worker.stop()
            if worker.isRunning():
                worker.wait(1200)
            else:
                worker.deleteLater()

    def _request_ticket(self, conversation_id):
        if not self.token or not self.active_conversation or self.active_conversation.get("id") != conversation_id:
            return
        self._request("ticket:" + conversation_id, "/api/chat/ticket", "POST", {"conversationId": conversation_id})

    def _start_socket(self, conversation_id, ticket):
        if not ticket or not self.active_conversation or self.active_conversation.get("id") != conversation_id:
            return
        self._close_socket()
        generation = self._socket_generation
        try:
            url = websocket_url(self.api_base, ticket)
        except ValueError as exc:
            self.status_label.setText(str(exc))
            return
        worker = _ChatSocket(url)
        _ACTIVE_SOCKETS.add(worker)
        worker.event_received.connect(lambda packet, g=generation: self._on_socket_event(g, packet))
        worker.state_changed.connect(lambda message, g=generation: self._on_socket_state(g, message, conversation_id))
        worker.finished.connect(lambda w=worker: _ACTIVE_SOCKETS.discard(w))
        worker.finished.connect(worker.deleteLater)
        self._socket = worker
        worker.start()
        self.status_label.setText("Connecting to live chat…")

    def _on_socket_state(self, generation, message, conversation_id):
        if generation != self._socket_generation:
            return
        self.status_label.setText(message)
        if message == "Connected":
            self._retry_count = 0
            self.message_edit.setEnabled(True)
            self.send_button.setEnabled(True)
            self._request("history:" + conversation_id, "/api/conversations/" + urllib.parse.quote(conversation_id, safe="") + "/messages?limit=100")
        elif message.startswith("Disconnected") or message.startswith("Connection error") or message.startswith("Connection closed"):
            self.message_edit.setEnabled(False)
            self.send_button.setEnabled(False)
            self._schedule_reconnect(conversation_id)

    def _schedule_reconnect(self, conversation_id):
        if self._reconnect_pending or not self.token or not self.active_conversation or self.active_conversation.get("id") != conversation_id:
            return
        self._reconnect_pending = True
        delay = min(30000, 1000 * (2 ** min(self._retry_count, 5)))
        self._retry_count += 1
        self.status_label.setText("Disconnected · reconnecting in %s seconds" % max(1, delay // 1000))
        def reconnect():
            self._reconnect_pending = False
            if self.token and self.active_conversation and self.active_conversation.get("id") == conversation_id:
                self._request_ticket(conversation_id)
        QTimer.singleShot(delay, reconnect)

    def _on_socket_event(self, generation, packet):
        if generation != self._socket_generation:
            return
        if packet.get("type") == "message" and isinstance(packet.get("message"), dict):
            message = packet["message"]
            self.messages.append(message)
            self._render_messages()
            return
        if packet.get("type") == "error":
            self.status_label.setText(str(packet.get("message") or "Chat error"))

    def _render_messages(self):
        self.history.clear()
        if isinstance(self.messages, dict):
            msg_list = sorted(self.messages.values(), key=lambda item: int(item.get("id", 0)))
        elif isinstance(self.messages, list):
            msg_list = sorted(self.messages, key=lambda item: int(item.get("id", 0)))
        else:
            msg_list = []

        if not msg_list:
            if self.current_role == "Support":
                self.history.setHtml("<p style='color:#64748b;padding:12px;'>No messages in this conversation yet. Send a message to start.</p>")
            else:
                self.history.setHtml("<p style='color:#64748b;padding:12px;'>Send a message to reach our Support team directly.</p>")
            return

        fragments = []
        is_dark = False
        if hasattr(self, "db") and hasattr(self.db, "get_setting"):
            try:
                is_dark = (self.db.get_setting("ui_theme", "day") in ("night", "dark"))
            except Exception:
                is_dark = False

        for msg in msg_list:
            sender_role = str(msg.get("sender_role") or "User")
            sender_name = html.escape(str(msg.get("sender_name") or msg.get("display_name") or msg.get("username") or "User"))
            stamp = html.escape(str(msg.get("created_at") or "")[:19].replace("T", " "))
            body = html.escape(str(msg.get("text") or "")).replace("\n", "<br>")

            is_own = (self.current_role == "User" and sender_role == "User") or (self.current_role == "Support" and sender_role == "Support") or (int(msg.get("sender_user_id") or 0) == int((self.chat_user or {}).get("id") or -1) if self.chat_user else False)

            if is_own:
                display_label = f"{sender_name} (You)"
                align = "right"
                if is_dark:
                    bubble_bg = "#1E293B"
                    bubble_border = "#334155"
                    sender_color = "#38BDF8"
                    stamp_color = "#94A3B8"
                    text_color = "#F8FAFC"
                else:
                    bubble_bg = "#F1F5F9"
                    bubble_border = "#CBD5E1"
                    sender_color = "#2563EB"
                    stamp_color = "#64748B"
                    text_color = "#0F172A"
            else:
                display_label = sender_name
                align = "left"
                if is_dark:
                    bubble_bg = "#0F172A"
                    bubble_border = "#334155"
                    sender_color = "#2DD4BF"
                    stamp_color = "#94A3B8"
                    text_color = "#F8FAFC"
                else:
                    bubble_bg = "#FFFFFF"
                    bubble_border = "#E2E8F0"
                    sender_color = "#0D9488"
                    stamp_color = "#64748B"
                    text_color = "#0F172A"

            fragments.append(
                f'<table width="100%" border="0" cellpadding="0" cellspacing="0" style="margin:4px 0;">'
                f'<tr><td align="{align}">'
                f'<table border="0" cellpadding="8" cellspacing="0" style="background-color:{bubble_bg};border:1.5px solid {bubble_border};border-radius:10px;">'
                f'<tr><td>'
                f'<div style="font-size:10px;font-weight:bold;color:{sender_color};margin-bottom:2px;">{display_label} &nbsp; <span style="font-weight:normal;color:{stamp_color};font-size:9.5px;">{stamp}</span></div>'
                f'<div style="font-size:12px;line-height:1.4;color:{text_color};white-space:normal;overflow-wrap:anywhere;">{body}</div>'
                f'</td></tr></table>'
                f'</td></tr></table>'
            )

        body_bg = "#0B1120" if is_dark else "transparent"
        self.history.setHtml(f"<html><body style='font-family:Segoe UI,DejaVu Sans,sans-serif;font-size:12px;margin:6px;background:{body_bg};'>" + "".join(fragments) + "</body></html>")
        cursor = self.history.textCursor()
        cursor.clearSelection()
        cursor.movePosition(cursor.MoveOperation.End)
        self.history.setTextCursor(cursor)
        scrollbar = self.history.verticalScrollBar()
        if scrollbar is not None:
            scrollbar.setValue(scrollbar.maximum())

    def _send_message(self):
        text = self.message_edit.text().strip()
        if not text:
            return
        conv_id = str(self.active_conversation.get("id")) if self.active_conversation else ""
        if not conv_id:
            return
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        sender_role = self.current_role or "User"
        sender_name = self.current_display_name or ("Support" if sender_role == "Support" else "User")

        if hasattr(self.db, "conn") and self.db.conn is not None:
            self.db.conn.execute(
                "INSERT INTO local_chat_messages (conversation_id, sender_role, sender_name, text, created_at) VALUES (?, ?, ?, ?, ?)",
                (conv_id, sender_role, sender_name, text, now_str)
            )
            last_preview = text if sender_role == "User" else f"Support: {text}"
            self.db.conn.execute(
                "UPDATE local_chat_conversations SET last_message=?, updated_at=? WHERE id=?",
                (last_preview, now_str, conv_id)
            )
            self.db.conn.commit()

        base = self._base()
        if base:
            def _async_send():
                try:
                    payload = {
                        "conversation_id": conv_id,
                        "sender_role": sender_role,
                        "sender_name": sender_name,
                        "text": text,
                    }
                    _api_call(base, "/api/support/send", "", "POST", payload)
                except Exception:
                    pass
            threading.Thread(target=_async_send, name="chat-send", daemon=True).start()

        worker = self._socket
        if worker is not None and worker.isRunning():
            import uuid
            worker.send_packet({"type": "message", "text": text, "clientMessageId": str(uuid.uuid4())})

        self.message_edit.clear()
        self._reload_messages()
        if self.current_role == "Support":
            self._reload_conversations()

    def _new_private(self):
        if not self.users:
            self._request("users", "/api/users")
            QMessageBox.information(self, "Private chat", "Loading the employee directory. Please try again in a moment.")
            return
        names = [str(u.get("username")) for u in self.users if str(u.get("username", "")).lower() != str((self.chat_user or {}).get("username", "")).lower()]
        if not names:
            QMessageBox.information(self, "Private chat", "No other active chat accounts exist yet.")
            return
        username, accepted = QInputDialog.getItem(self, "Start a private chat", "Employee username", names, 0, False)
        if accepted and username:
            self._request("private", "/api/conversations/private", "POST", {"username": username})

    def _new_group(self):
        name, accepted = QInputDialog.getText(self, "Create group", "Group name")
        if not accepted or not name.strip():
            return
        usernames, accepted = QInputDialog.getText(self, "Create group", "Member usernames (comma-separated)")
        if not accepted:
            return
        members = [value.strip() for value in usernames.split(",") if value.strip()]
        self._request("group", "/api/conversations/group", "POST", {"name": name.strip(), "usernames": members})

    def _add_group_member(self):
        conversation = self.active_conversation
        if not conversation or conversation.get("kind") != "group":
            return
        username, accepted = QInputDialog.getText(self, "Add group member", "Existing chat username")
        if not accepted or not username.strip():
            return
        path = "/api/conversations/" + urllib.parse.quote(str(conversation["id"]), safe="") + "/members"
        self._request("add-member", path, "POST", {"username": username.strip()})

    def _change_password(self):
        current, accepted = QInputDialog.getText(
            self, "Change chat password", "Current chat password", QLineEdit.EchoMode.Password
        )
        if not accepted or not current:
            return
        new_password, accepted = QInputDialog.getText(
            self, "Change chat password", "New password (10+ characters, letters and numbers)",
            QLineEdit.EchoMode.Password,
        )
        if not accepted or not new_password:
            return
        self._request("change-password", "/api/auth/password", "POST", {
            "currentPassword": current, "newPassword": new_password,
        })

    def _create_chat_account(self):
        username, accepted = QInputDialog.getText(self, "Create chat account", "Username")
        if not accepted or not username.strip():
            return
        display_name, accepted = QInputDialog.getText(self, "Create chat account", "Display name")
        if not accepted:
            return
        password, accepted = QInputDialog.getText(
            self, "Create chat account", "Temporary password (10+ characters)",
            QLineEdit.EchoMode.Password,
        )
        if not accepted:
            return
        role, accepted = QInputDialog.getItem(self, "Create chat account", "Role", ["HR", "Admin"], 0, False)
        if not accepted:
            return
        self._request("create-user", "/api/admin/users", "POST", {
            "username": username.strip(), "displayName": display_name.strip(),
            "password": password, "role": role,
        })

    def _logout(self):
        if hasattr(self, "_conversation_refresh_timer"):
            self._conversation_refresh_timer.stop()
        self._refresh_inflight = False
        self._close_socket()
        self.token = ""
        self.db.set_setting("cloudflare_chat_session", "")
        self.current_role = ""
        self.current_display_name = ""
        self.chat_user = None
        self.users = []
        self.conversations = []
        self.active_conversation = None
        self.messages = []
        self.conversation_list.clear()
        self.history.clear()
        self.password_edit.clear()
        self.login_error.clear()
        self.chat_panel.hide()
        self.login_panel.show()
        self.role_badge.setText("Mode: Sign In Required")
        self.status_label.setText("Not connected")

    def shutdown(self):
        """Stop polling and socket before the parent application closes."""
        if hasattr(self, "_poll_timer") and self._poll_timer.isActive():
            self._poll_timer.stop()
        if hasattr(self, "_conversation_refresh_timer") and self._conversation_refresh_timer.isActive():
            self._conversation_refresh_timer.stop()
        self._close_socket()

    def closeEvent(self, event):
        self.shutdown()
        super().closeEvent(event)
