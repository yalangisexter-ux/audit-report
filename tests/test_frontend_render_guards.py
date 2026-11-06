from pathlib import Path

APP_SOURCE = Path(__file__).resolve().parents[1] / "frontend" / "src" / "App.jsx"


def test_clock_header_does_not_reference_undefined_busy_state():
    source = APP_SOURCE.read_text(encoding="utf-8")
    assert "disabled={clockModeBusy}" not in source
    assert 'aria-label={"Switch to "+(clockMode===' in source


def test_unauthenticated_mobile_view_keeps_login_content_renderable():
    source = APP_SOURCE.read_text(encoding="utf-8")
    assert 'if(!checked)return <div className="grid min-h-screen' in source
    assert 'if(!user)return <div className="login-screen grid min-h-screen' in source
    assert "Sign in" in source
