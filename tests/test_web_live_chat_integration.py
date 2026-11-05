from pathlib import Path

from cloudflare_chat import FALLBACK_CHAT_API_BASE


ROOT = Path(__file__).resolve().parents[1]


def test_main_web_navigation_embeds_the_full_live_chat_client():
    app_source = (ROOT / "frontend" / "src" / "App.jsx").read_text(encoding="utf-8")
    component = (ROOT / "frontend" / "src" / "LiveChat.jsx").read_text(encoding="utf-8")
    worker_config = (ROOT / "cloudflare-chat" / "wrangler.toml").read_text(encoding="utf-8")

    assert "import LiveChat from './LiveChat';" in app_source
    assert "{tab==='chat'&&<Panel title=\"Live Chat\"><LiveChat/></Panel>}" in app_source
    assert "data.messages.map" not in app_source

    assert f"const DEFAULT_CHAT_URL = '{FALLBACK_CHAT_API_BASE}'" in component
    assert "VITE_CHAT_WORKER_URL" in component
    assert 'title="Raw Strength private and group Live Chat"' in component
    assert 'allow="camera; microphone; display-capture; fullscreen"' in component
    assert 'target="_blank"' in component
    assert 'rel="noopener noreferrer"' in component
    assert "membership and message access are enforced by the chat service" in component
    assert 'directory = "../chat-web"' in worker_config


def test_embedded_chat_keeps_a_separate_authentication_boundary():
    component = (ROOT / "frontend" / "src" / "LiveChat.jsx").read_text(encoding="utf-8")

    assert "Your audit login is not shared with the chat service." in component
    assert "Use the chat service sign-in inside this panel" in component



def test_general_channel_history_and_send_action_remain_available():
    app_source = (ROOT / "frontend" / "src" / "App.jsx").read_text(encoding="utf-8")
    component = (ROOT / "frontend" / "src" / "LiveChat.jsx").read_text(encoding="utf-8")

    assert "messages={data.messages}" in app_source
    assert "onSendGeneral={async content=>" in app_source
    assert "channel:'general'" in app_source
    assert 'role="tablist"' in component
    assert 'aria-label="General channel messages"' in component
    assert "messages.map(" in component
    assert "onSendGeneral(content)" in component
    assert "General Channel" in component
