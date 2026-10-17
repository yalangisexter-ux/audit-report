import pytest
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QMessageBox
import app


@pytest.fixture
def qt_app():
    return QApplication.instance() or QApplication([])


def test_popup_dialog_sizing_and_wordwrap(qt_app, monkeypatch):
    """Verify popup dialogs enforce minimum 480px width, word-wrapped label, and unclipped icons."""
    app.apply_app_theme(qt_app, "day")

    captured_boxes = []

    def mock_hook(box):
        captured_boxes.append(box)
        assert box.minimumWidth() >= 480, f"Dialog minimum width {box.minimumWidth()} is less than 480"
        label = box.findChild(QLabel, "qt_msgbox_label")
        assert label is not None, "qt_msgbox_label not found"
        assert label.wordWrap() is True, "qt_msgbox_label wordWrap must be True"
        assert label.minimumWidth() >= 360, f"Label minimum width {label.minimumWidth()} is less than 360"

        icon_label = box.findChild(QLabel, "qt_msgboxex_icon_label")
        if icon_label is not None:
            assert icon_label.minimumWidth() >= 40, "Icon label must not be collapsed"
            assert icon_label.minimumHeight() >= 40, "Icon label height must not be collapsed"

        for btn in box.findChildren(QPushButton):
            assert btn.minimumWidth() >= 80, "Buttons must have adequate tactile width"
            assert btn.minimumHeight() >= 30, "Buttons must have adequate tactile height"
        return int(QMessageBox.StandardButton.No)

    monkeypatch.setattr(app, "_SHOW_DIALOG_HOOK", mock_hook)

    res = app.ask(
        None,
        "Pull latest database data",
        "This replaces local business records with the latest committed snapshot for this installation. "
        "A backup will be created first. Local accounts and settings will be preserved. Continue?",
    )
    assert res is False
    assert len(captured_boxes) == 1


def test_info_and_error_helpers(qt_app, monkeypatch):
    """Verify info and error helper functions set correct icons and standard buttons."""
    captured = []

    def mock_hook(box):
        captured.append(box)
        return int(QMessageBox.StandardButton.Ok)

    monkeypatch.setattr(app, "_SHOW_DIALOG_HOOK", mock_hook)

    # Test info
    app.info(None, "Information notification test")
    assert len(captured) == 1
    assert captured[0].icon() == QMessageBox.Icon.Information

    # Test error
    app.error(None, "Error notification test")
    assert len(captured) == 2
    assert captured[1].icon() == QMessageBox.Icon.Critical


def test_theme_awareness_day_and_night(qt_app, monkeypatch):
    """Verify dialog styling automatically adapts to active day and night themes."""
    captured = []

    def mock_hook(box):
        captured.append(box)
        return int(QMessageBox.StandardButton.Ok)

    monkeypatch.setattr(app, "_SHOW_DIALOG_HOOK", mock_hook)

    # Day theme
    app.apply_app_theme(qt_app, "day")
    app.info(None, "Day theme check")
    assert len(captured) == 1
    assert "#FFFFFF" in captured[0].styleSheet() or "#0F172A" in captured[0].styleSheet()

    # Night theme
    app.apply_app_theme(qt_app, "night")
    app.info(None, "Night theme check")
    assert len(captured) == 2
    assert "#0F172A" in captured[1].styleSheet()
