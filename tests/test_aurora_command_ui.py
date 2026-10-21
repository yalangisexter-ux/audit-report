import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import QApplication

import aurora_command_ui as aurora


@pytest.fixture
def qt_app():
    return QApplication.instance() or QApplication([])


def test_neon_sparkline_card(qt_app):
    card = aurora.NeonSparklineCard("TEST KPI:", "$123.4M", "#00F0FF", [0.1, 0.5, 0.9])
    card.resize(300, 90)
    card.show()

    # Verify painting
    pixmap = QPixmap(300, 90)
    card.render(pixmap)
    assert not pixmap.isNull()

    card.set_data("$999.9M", [0.2, 0.8])
    assert card.value_text == "$999.9M"
    card.close()


def test_enterprise_flow_widget(qt_app):
    flow = aurora.EnterpriseFlowWidget()
    flow.resize(800, 320)
    flow.show()

    pixmap = QPixmap(800, 320)
    flow.render(pixmap)
    assert not pixmap.isNull()
    flow.close()


def test_matrix_grid_widget(qt_app):
    grid = aurora.MatrixGridWidget()
    grid.resize(700, 350)
    assert grid.table.rowCount() == 7
    assert grid.table.columnCount() == 6
    assert len(grid.sliders) == 7

    # Check slider interactivity
    first_slider = grid.sliders[0]
    first_slider.setValue(75)
    assert first_slider.value() == 75
    grid.close()


def test_radar_risk_widget(qt_app):
    radar = aurora.RadarRiskWidget()
    radar.resize(250, 200)
    radar.show()

    pixmap = QPixmap(250, 200)
    radar.render(pixmap)
    assert not pixmap.isNull()
    assert len(radar.axes) == 6
    radar.close()


def test_aurora_command_hud_assembly(qt_app):
    hud = aurora.AuroraCommandHUD()
    hud.resize(1100, 750)
    hud.show()

    assert hud.flow_widget is not None
    assert hud.matrix_grid is not None
    assert hud.radar_widget is not None
    assert hud.heatmap_widget is not None
    assert hud.action_pills is not None

    pixmap = QPixmap(1100, 750)
    hud.render(pixmap)
    assert not pixmap.isNull()
    hud.close()
