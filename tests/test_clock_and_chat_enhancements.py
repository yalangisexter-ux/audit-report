import os
import sqlite3
import pytest
from datetime import datetime
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

import app
from app import MainWindow, AnalogClockWidget
from cloudflare_chat import CloudflareChatTab, setup_chat_tables, verify_developer_password


@pytest.fixture
def qt_app():
    return QApplication.instance() or QApplication([])


def _make_window(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    qt_app = app.QApplication.instance() or app.QApplication([])
    monkeypatch.setattr(app, "DB_PATH", str(tmp_path / "test-clock-tabs.db"))
    monkeypatch.setattr(app, "BACKUP_DIR", str(tmp_path / "backups"))
    database = app.Database()
    window = app.MainWindow(database, {"username": "Admin QA", "role": "Admin", "display_name": "Admin User"})
    return qt_app, database, window


@pytest.fixture
def memory_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    setup_chat_tables(conn)

    class MockDB:
        def __init__(self, c):
            self.conn = c
            self.settings = {}

        def get_setting(self, key, default=""):
            return self.settings.get(key, default)

        def set_setting(self, key, value):
            self.settings[key] = str(value)

    return MockDB(conn)


def test_analog_clock_widget_and_signals(qt_app):
    widget = AnalogClockWidget()
    now = datetime(2026, 10, 16, 14, 30, 45)
    widget.set_time(now)
    assert widget._current_time == now

    clicked_received = []
    widget.clicked.connect(lambda: clicked_received.append(True))
    event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(10.0, 10.0),
        QPointF(10.0, 10.0),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    widget.mousePressEvent(event)
    assert clicked_received == [True]


def test_clock_mode_toggle_and_persistence(tmp_path, monkeypatch):
    qt_app, database, window = _make_window(tmp_path, monkeypatch)
    try:
        # Default mode should be digital
        assert getattr(window, "_clock_mode", "digital") == "digital"
        assert not window.header_clock.isHidden()

        # Toggle to analog
        window.toggle_clock_mode()
        assert window._clock_mode == "analog"
        assert not window.header_clock_analog.isHidden()
        assert window.header_clock.isHidden()
        assert window.clock_mode_btn.text() == "🔢"
        assert database.get_setting("clock_mode") == "analog"

        # Toggle back to digital
        window.toggle_clock_mode()
        assert window._clock_mode == "digital"
        assert not window.header_clock.isHidden()
        assert window.header_clock_analog.isHidden()
        assert window.clock_mode_btn.text() == "🕒"
        assert database.get_setting("clock_mode") == "digital"

        # Settings dropdown synchronization
        if hasattr(window, "clock_mode_combo"):
            window.clock_mode_combo.setCurrentText("Analog")
            assert window._clock_mode == "analog"
            window.clock_mode_combo.setCurrentText("Digital")
            assert window._clock_mode == "digital"
    finally:
        window.close()
        database.conn.close()


def test_unwanted_tab_headers_omitted_across_tabs(tmp_path, monkeypatch):
    qt_app, database, window = _make_window(tmp_path, monkeypatch)
    try:
        # Check that tabs do not have a child widget named "pageHeader"
        for tab_widget in [
            window.employees_tab,
            window.tasks_tab,
            window.reports_tab,
            window.tracker_tab,
            window.attendance_tab,
            window.archive_tab,
            window.settings_tab,
            window.business_tab,
            window.chat_tab,
        ]:
            header = tab_widget.findChild(app.QWidget, "pageHeader")
            assert header is None, f"Tab {tab_widget} unexpectedly contains a redundant pageHeader"

        # BusinessTrackingTab should not have pageTitle or pageSubtitle property labels
        page_titles = [w for w in window.business_tab.findChildren(app.QLabel) if w.property("pageTitle")]
        assert len(page_titles) == 0
    finally:
        window.close()
        database.conn.close()


def test_verify_developer_password():
    assert not verify_developer_password("")
    assert not verify_developer_password("wrong_password_123")
    assert verify_developer_password("Devlopershouse@1996#")
    # Verify with environment variable override
    os.environ["DEVELOPER_PASSWORD"] = "emergency_dev_key_2026"
    try:
        assert verify_developer_password("emergency_dev_key_2026")
    finally:
        os.environ.pop("DEVELOPER_PASSWORD", None)


def test_live_chat_user_and_support_flow(qt_app, memory_db, monkeypatch):
    os.environ["DEVELOPER_PASSWORD"] = "dev_secret_auth"
    try:
        chat = CloudflareChatTab(memory_db, {"id": 2, "username": "rahul", "display_name": "Rahul"})
        chat.show()
        qt_app.processEvents()

        # Initial state: login panel visible, chat panel hidden
        assert not chat.login_panel.isHidden()
        assert chat.chat_panel.isHidden()
        assert chat.role_combo.count() == 2

        # 1. Customer connects with name, no password asked
        assert chat.role_combo.currentIndex() == 0  # User (Customer)
        assert not chat.name_row_label.isHidden()
        assert not chat.user_name_edit.isHidden()
        assert chat.password_edit.isHidden()

        chat.user_name_edit.setText("Rahul Verma")
        chat._handle_connect()
        qt_app.processEvents()

        # Should be connected as User
        assert chat.current_role == "User"
        assert chat.current_display_name == "Rahul Verma"
        assert not chat.chat_panel.isHidden()
        assert chat.login_panel.isHidden()
        assert chat.active_conversation is not None
        assert chat.active_conversation["user_name"] == "Rahul Verma"

        # Send user message
        chat.message_edit.setText("Hello Support team, I have a query about my tasks.")
        chat._send_message()

        # Verify message stored in local DB
        cur = memory_db.conn.cursor()
        cur.execute("SELECT sender_role, sender_name, text FROM local_chat_messages WHERE conversation_id=?", (chat.active_conversation["id"],))
        rows = cur.fetchall()
        assert len(rows) == 1
        assert rows[0][0] == "User"
        assert rows[0][1] == "Rahul Verma"
        assert rows[0][2] == "Hello Support team, I have a query about my tasks."

        # User logs out
        chat._logout()
        qt_app.processEvents()
        assert not chat.login_panel.isHidden()
        assert chat.chat_panel.isHidden()

        # 2. Support login with developer password
        chat.role_combo.setCurrentIndex(1)  # Support
        qt_app.processEvents()
        assert chat.name_row_label.isHidden()
        assert not chat.password_edit.isHidden()

        # Bad password fails
        chat.password_edit.setText("wrong")
        chat._handle_connect()
        qt_app.processEvents()
        assert "Developer authorization failed" in chat.login_error.text()
        assert chat.chat_panel.isHidden()

        # Correct developer password succeeds
        chat.password_edit.setText("dev_secret_auth")
        chat._handle_connect()
        qt_app.processEvents()
        assert chat.current_role == "Support"
        assert not chat.chat_panel.isHidden()

        # Support can see all user conversations
        assert len(chat.conversations) >= 1
        rahul_conv = next((c for c in chat.conversations if c["user_name"] == "Rahul Verma"), None)
        assert rahul_conv is not None

        # Support can switch conversation to Rahul
        chat._open_conversation(rahul_conv)
        assert chat.active_conversation["id"] == rahul_conv["id"]
        assert len(chat.messages) == 1
        assert "Hello Support team" in chat.history.toPlainText()

        # Support replies to Rahul
        chat.message_edit.setText("Hello Rahul, Support is here to help!")
        chat._send_message()

        # Verify reply stored
        cur.execute("SELECT sender_role, text FROM local_chat_messages WHERE conversation_id=? ORDER BY id ASC", (rahul_conv["id"],))
        all_msgs = cur.fetchall()
        assert len(all_msgs) == 2
        assert all_msgs[1][0] == "Support"
        assert all_msgs[1][1] == "Hello Rahul, Support is here to help!"

        # 3. Another user connects and texts
        safe_mary_id = "user_mary_jones"
        memory_db.conn.execute(
            "INSERT INTO local_chat_conversations (id, user_name, last_message, updated_at) VALUES (?, ?, ?, ?)",
            (safe_mary_id, "Mary Jones", "Leave request question", "2026-10-16 11:00:00")
        )
        memory_db.conn.execute(
            "INSERT INTO local_chat_messages (conversation_id, sender_role, sender_name, text, created_at) VALUES (?, ?, ?, ?, ?)",
            (safe_mary_id, "User", "Mary Jones", "Leave request question", "2026-10-16 11:00:00")
        )
        memory_db.conn.commit()

        # Support poll updates picks up Mary
        chat._poll_updates()
        assert any(c["user_name"] == "Mary Jones" for c in chat.conversations)

        # Support switches conversation to Mary
        mary_conv = next(c for c in chat.conversations if c["user_name"] == "Mary Jones")
        chat._open_conversation(mary_conv)
        assert chat.active_conversation["id"] == safe_mary_id
        assert "Leave request question" in chat.history.toPlainText()

        # Support replies to Mary
        chat.message_edit.setText("Hi Mary, your leave request has been approved.")
        chat._send_message()

        cur.execute("SELECT sender_role, text FROM local_chat_messages WHERE conversation_id=? ORDER BY id ASC", (safe_mary_id,))
        mary_msgs = cur.fetchall()
        assert len(mary_msgs) == 2
        assert mary_msgs[1][0] == "Support"
        assert mary_msgs[1][1] == "Hi Mary, your leave request has been approved."

        # Support switches back to Rahul
        chat._open_conversation(rahul_conv)
        assert chat.active_conversation["id"] == rahul_conv["id"]
        assert "Hello Rahul, Support is here to help!" in chat.history.toPlainText()

        chat.shutdown()
        chat.close()
    finally:
        os.environ.pop("DEVELOPER_PASSWORD", None)
