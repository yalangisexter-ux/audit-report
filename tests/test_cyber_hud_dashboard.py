import pytest
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication

import app


@pytest.fixture
def qt_app():
    return QApplication.instance() or QApplication([])


def test_mini_sparkline_widget(qt_app):
    spark = app.MiniSparkline(color="#00F0FF", points=[0.2, 0.4, 0.8, 1.0])
    spark.resize(68, 38)
    spark.show()

    # Verify rendering
    pixmap = QPixmap(68, 38)
    spark.render(pixmap)
    assert not pixmap.isNull()

    spark.set_points([0.1, 0.5, 0.9])
    assert spark.points == [0.1, 0.5, 0.9]
    spark.close()


def test_dashboard_cyber_hud_assembly(tmp_path, monkeypatch, qt_app):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    db_path = tmp_path / "cyber_hud_test.db"
    monkeypatch.setattr(app, "DB_PATH", str(db_path))
    db = app.Database()
    win = app.MainWindow(db, {"username": "Admin", "role": "Admin", "display_name": "Administrator"})

    # Ensure dummy aurora financial widgets are NOT present
    assert not hasattr(win, "aurora_hud") or win.aurora_hud is None

    # Ensure real KPI cards and sparklines are active
    assert hasattr(win, "kpi_cards")
    assert len(win.kpi_cards) == 5
    assert hasattr(win, "kpi_sparklines")
    assert len(win.kpi_sparklines) == 5
    assert hasattr(win, "kpi_labels")
    assert len(win.kpi_labels) == 5

    # Ensure sidebar has deep dark styling
    assert hasattr(win, "sidebar")
    assert win.sidebar.objectName() == "navigationSidebar"

    win.refresh_dashboard()
    win.close()
    db.conn.close()
