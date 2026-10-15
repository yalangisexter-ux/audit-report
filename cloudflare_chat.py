"""Cloudflare-powered live chat tab for the Raw Strength desktop application.

Chat credentials and bearer tokens remain in memory only. The existing local
employee-audit login and SQLite business records are not sent to Cloudflare.
"""
from __future__ import annotations

import html
import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from urllib.parse import urlsplit, urlunsplit

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QTextEdit, QInputDialog,
    QMessageBox, QFrame, QSizePolicy
)

_ACTIVE_REQUESTS = set()
_ACTIVE_SOCKETS = set()

try:
    import websocket
except ImportError:  # The packaged build installs websocket-client from requirements.txt.
    websocket = None


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
    headers = {"Accept": "application/json", "Cache-Control": "no-store"}
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
        self.token = ""
        self.chat_user = None
        self.api_base = str(self.db.get_setting("cloudflare_chat_api_url", "") or "")
        self.conversations = []
        self.users = []
        self.active_conversation = None
        self.messages = {}
        self._workers = set()
        self._socket = None
        self._socket_generation = 0
        self._retry_count = 0
        self._reconnect_pending = False
        self._current_ticket_request = ""
        self._preferred_conversation_id = ""
        self._build_ui()
        if websocket is None:
            self.status_label.setText("Install websocket-client to enable live delivery.")
            self.status_label.setStyleSheet("color:#b91c1c;")

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)

        heading = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Live Chat")
        title.setStyleSheet("font-size:22px;font-weight:700;color:#312e81;")
        subtitle = QLabel("Private employee conversations and authorized team groups")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color:#64748b;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        heading.addLayout(title_box, 1)
        self.status_label = QLabel("Not connected")
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.status_label.setStyleSheet("color:#64748b;font-size:12px;")
        heading.addWidget(self.status_label)
        root.addLayout(heading)

        self.login_panel = QFrame()
        self.login_panel.setObjectName("chatLoginPanel")
        self.login_panel.setStyleSheet("#chatLoginPanel{background:rgba(255,255,255,220);border:1px solid #ddd6fe;border-radius:16px;}")
        login_layout = QVBoxLayout(self.login_panel)
        login_layout.setContentsMargins(18, 16, 18, 16)
        login_layout.setSpacing(10)
        info = QLabel("Cloud chat has separate credentials. Your existing Audit Manager login and local business data are not uploaded.")
        info.setWordWrap(True)
        info.setStyleSheet("color:#475569;")
        login_layout.addWidget(info)
        form = QFormLayout()
        self.endpoint_edit = QLineEdit(self.api_base)
        self.endpoint_edit.setPlaceholderText("https://your-worker.your-subdomain.workers.dev")
        self.endpoint_edit.setClearButtonEnabled(True)
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Chat username")
        self.username_edit.setText(str(self.current_user.get("username", "") or ""))
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("Chat password")
        self.password_edit.returnPressed.connect(self._login)
        form.addRow("Cloudflare Worker URL", self.endpoint_edit)
        form.addRow("Chat username", self.username_edit)
        form.addRow("Chat password", self.password_edit)
        login_layout.addLayout(form)
        self.login_error = QLabel("")
        self.login_error.setWordWrap(True)
        self.login_error.setStyleSheet("color:#b91c1c;")
        login_layout.addWidget(self.login_error)
        login_buttons = QHBoxLayout()
        login_buttons.addStretch(1)
        self.login_button = QPushButton("Sign in to Live Chat")
        self.login_button.setMinimumHeight(38)
        self.login_button.setStyleSheet("QPushButton{background:#6d28d9;color:white;border:0;border-radius:9px;padding:8px 16px;font-weight:700;} QPushButton:hover{background:#5b21b6;}")
        self.login_button.clicked.connect(self._login)
        login_buttons.addWidget(self.login_button)
        login_layout.addLayout(login_buttons)
        root.addWidget(self.login_panel)

        self.chat_panel = QFrame()
        self.chat_panel.setObjectName("chatMainPanel")
        self.chat_panel.setStyleSheet("#chatMainPanel{background:rgba(255,255,255,225);border:1px solid #ddd6fe;border-radius:16px;}")
        chat_layout = QHBoxLayout(self.chat_panel)
        chat_layout.setContentsMargins(10, 10, 10, 10)
        chat_layout.setSpacing(10)

        left = QVBoxLayout()
        left.setSpacing(8)
        action_row = QHBoxLayout()
        self.private_button = QPushButton("+ Private")
        self.group_button = QPushButton("+ Group")
        self.admin_button = QPushButton("Add account")
        for button in (self.private_button, self.group_button, self.admin_button):
            button.setMinimumHeight(34)
            button.setStyleSheet("QPushButton{background:#f5f3ff;color:#4c1d95;border:1px solid #ddd6fe;border-radius:8px;padding:5px 8px;} QPushButton:hover{background:#ede9fe;}")
            action_row.addWidget(button)
        left.addLayout(action_row)
        self.conversation_list = QListWidget()
        self.conversation_list.setMinimumWidth(200)
        self.conversation_list.setMaximumWidth(310)
        self.conversation_list.setStyleSheet("QListWidget{background:rgba(248,250,252,235);color:#0f172a;border:1px solid #e2e8f0;border-radius:10px;padding:4px;} QListWidget::item{padding:10px;border-radius:7px;} QListWidget::item:selected{background:#ddd6fe;color:#312e81;}")
        self.conversation_list.currentItemChanged.connect(self._select_conversation)
        left.addWidget(self.conversation_list, 1)
        self.add_member_button = QPushButton("Add member to selected group")
        self.add_member_button.clicked.connect(self._add_group_member)
        self.add_member_button.setStyleSheet("QPushButton{background:#fff;color:#4c1d95;border:1px solid #ddd6fe;border-radius:8px;padding:7px;}")
        left.addWidget(self.add_member_button)
        self.logout_button = QPushButton("Sign out of Live Chat")
        self.logout_button.clicked.connect(self._logout)
        left.addWidget(self.logout_button)
        self.change_password_button = QPushButton("Change chat password")
        self.change_password_button.clicked.connect(self._change_password)
        left.addWidget(self.change_password_button)

        right = QVBoxLayout()
        right.setSpacing(8)
        self.conversation_heading = QLabel("Choose a conversation")
        self.conversation_heading.setStyleSheet("font-size:16px;font-weight:700;color:#1e1b4b;")
        right.addWidget(self.conversation_heading)
        self.history = QTextEdit()
        self.history.setReadOnly(True)
        self.history.setAcceptRichText(False)
        self.history.setStyleSheet("QTextEdit{background:rgba(248,250,252,245);color:#0f172a;border:1px solid #e2e8f0;border-radius:10px;padding:10px;}")
        right.addWidget(self.history, 1)
        composer = QHBoxLayout()
        self.message_edit = QLineEdit()
        self.message_edit.setPlaceholderText("Write a message…")
        self.message_edit.setMaxLength(4000)
        self.message_edit.returnPressed.connect(self._send_message)
        self.send_button = QPushButton("Send")
        self.send_button.setMinimumWidth(86)
        self.send_button.setMinimumHeight(38)
        self.send_button.setStyleSheet("QPushButton{background:#6d28d9;color:white;border:0;border-radius:9px;padding:8px 14px;font-weight:700;} QPushButton:hover{background:#5b21b6;}")
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
        self.admin_button.hide()
        self.add_member_button.hide()
        self.send_button.setEnabled(False)
        self.message_edit.setEnabled(False)
        self.private_button.clicked.connect(self._new_private)
        self.group_button.clicked.connect(self._new_group)
        self.admin_button.clicked.connect(self._create_chat_account)

    def _base(self):
        try:
            base = normalize_api_base(self.endpoint_edit.text())
            self.api_base = base
            self.db.set_setting("cloudflare_chat_api_url", base)
            self.login_error.setText("")
            return base
        except ValueError as exc:
            self.login_error.setText(str(exc))
            return ""

    def _request(self, request_id, path, method="GET", payload=None, token=None):
        base = self.api_base or self._base()
        if not base:
            return
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
            if not self.token or not self.chat_user.get("id"):
                self.login_error.setText("The chat service returned an invalid session.")
                self.token = ""
                return
            self.login_panel.hide()
            self.chat_panel.show()
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
            self.messages = {int(item["id"]): item for item in (data.get("messages") or [])}
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

    def _render_conversations(self):
        selected_id = self.active_conversation.get("id") if self.active_conversation else ""
        self.conversation_list.blockSignals(True)
        self.conversation_list.clear()
        selected_item = None
        for conversation in self.conversations:
            title = str(conversation.get("title") or conversation.get("name") or "Conversation")
            preview = str(conversation.get("last_message") or ("Group chat" if conversation.get("kind") == "group" else "Private conversation"))
            item = QListWidgetItem(title + "\n" + preview[:80])
            item.setData(Qt.ItemDataRole.UserRole, conversation)
            item.setToolTip(title + "\n" + preview)
            self.conversation_list.addItem(item)
            if conversation.get("id") == selected_id:
                selected_item = item
        if selected_item is not None:
            self.conversation_list.setCurrentItem(selected_item)
        self.conversation_list.blockSignals(False)

    def _select_conversation(self, current, _previous=None):
        if not current:
            return
        conversation = current.data(Qt.ItemDataRole.UserRole)
        if conversation:
            self._open_conversation(conversation)

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

    def _open_conversation(self, conversation):
        if not conversation or conversation.get("id") == (self.active_conversation or {}).get("id"):
            return
        self._close_socket()
        self.active_conversation = conversation
        self.messages = {}
        self.conversation_heading.setText(str(conversation.get("title") or conversation.get("name") or "Conversation"))
        self.history.clear()
        self.message_edit.clear()
        self.message_edit.setEnabled(False)
        self.send_button.setEnabled(False)
        self.add_member_button.setVisible(
            conversation.get("kind") == "group" and (
                conversation.get("member_role") == "owner" or (self.chat_user or {}).get("role") == "Admin"
            )
        )
        self._render_conversations()
        conversation_id = str(conversation["id"])
        self._request("history:" + conversation_id, "/api/conversations/" + urllib.parse.quote(conversation_id, safe="") + "/messages?limit=100")
        self._request_ticket(conversation_id)

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
            try:
                self.messages[int(message["id"])] = message
            except (KeyError, TypeError, ValueError):
                return
            self._render_messages()
            return
        if packet.get("type") == "error":
            self.status_label.setText(str(packet.get("message") or "Chat error"))

    def _render_messages(self):
        self.history.clear()
        rows = sorted(self.messages.values(), key=lambda item: int(item.get("id", 0)))
        fragments = []
        for message in rows:
            name = html.escape(str(message.get("display_name") or message.get("username") or "Employee"))
            stamp = html.escape(str(message.get("created_at") or "")[:19].replace("T", " "))
            body = html.escape(str(message.get("text") or "")).replace("\n", "<br>")
            own = int(message.get("sender_user_id") or 0) == int((self.chat_user or {}).get("id") or -1)
            color = "#5b21b6" if own else "#334155"
            fragments.append(
                '<div style="margin:7px 0;padding:9px 11px;border-radius:10px;background:%s;color:#ffffff;">'
                '<div style="font-size:10px;color:#e2e8f0;font-weight:700;">%s &nbsp; %s</div>'
                '<div style="white-space:normal;overflow-wrap:anywhere;">%s</div></div>' % (color, name, stamp, body)
            )
        self.history.setHtml("<html><body style='font-family:Segoe UI,sans-serif;font-size:12px;'>" + "".join(fragments) + "</body></html>")
        cursor = self.history.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.history.setTextCursor(cursor)

    def _send_message(self):
        text = self.message_edit.text().strip()
        worker = self._socket
        if not text or worker is None or not worker.isRunning():
            return
        import uuid
        if worker.send_packet({"type": "message", "text": text, "clientMessageId": str(uuid.uuid4())}):
            self.message_edit.clear()
        else:
            self.status_label.setText("Message not sent · reconnecting")
            self.message_edit.setEnabled(False)
            self.send_button.setEnabled(False)
            if self.active_conversation:
                self._schedule_reconnect(str(self.active_conversation["id"]))

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
        self._close_socket()
        self.token = ""
        self.chat_user = None
        self.users = []
        self.conversations = []
        self.active_conversation = None
        self.messages = {}
        self.conversation_list.clear()
        self.history.clear()
        self.password_edit.clear()
        self.login_error.clear()
        self.chat_panel.hide()
        self.login_panel.show()
        self.admin_button.hide()
        self.status_label.setText("Signed out of Live Chat")

    def shutdown(self):
        """Stop the live socket before the parent application closes."""
        self._close_socket()

    def closeEvent(self, event):
        self._close_socket()
        super().closeEvent(event)
