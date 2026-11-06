from pathlib import Path

FRONTEND = Path(__file__).resolve().parents[1] / "frontend" / "src"
APP_SOURCE = FRONTEND / "App.jsx"
ENTRY_SOURCE = FRONTEND / "main.jsx"
ERROR_BOUNDARY_SOURCE = FRONTEND / "AppErrorBoundary.jsx"


def test_clock_header_does_not_reference_undefined_busy_state():
    source = APP_SOURCE.read_text(encoding="utf-8")
    assert "disabled={clockModeBusy}" not in source
    assert 'aria-label={"Switch to "+(clockMode===' in source


def test_unauthenticated_mobile_view_keeps_login_content_renderable():
    source = APP_SOURCE.read_text(encoding="utf-8")
    assert 'if(!checked)return <div className="grid min-h-screen' in source
    assert 'if(!user)return <div className="login-screen grid min-h-screen' in source
    assert "Sign in" in source


def test_root_react_app_is_wrapped_in_a_render_error_boundary():
    source = ENTRY_SOURCE.read_text(encoding="utf-8")
    assert "import AppErrorBoundary from './AppErrorBoundary.jsx';" in source
    assert "<AppErrorBoundary>" in source
    assert "</AppErrorBoundary>" in source


def test_render_error_boundary_shows_accessible_recovery_instead_of_blank_screen():
    source = ERROR_BOUNDARY_SOURCE.read_text(encoding="utf-8")
    assert "static getDerivedStateFromError()" in source
    assert 'role="alert"' in source
    assert "Workspace could not be loaded" in source
    assert "Reload workspace" in source
    assert "window.location.reload()" in source
