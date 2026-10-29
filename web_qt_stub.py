"""Install lightweight PySide6 stubs so api_server can import app.py on headless web hosts."""
from __future__ import annotations

import sys
from unittest.mock import MagicMock


def install_pyside_stubs() -> None:
    if "PySide6" in sys.modules and not isinstance(sys.modules.get("PySide6"), MagicMock):
        return

    core = MagicMock()
    core.Qt = MagicMock()
    core.Signal = MagicMock(return_value=MagicMock())
    core.Slot = MagicMock(return_value=lambda fn: fn)
    core.QObject = object
    core.QThread = object
    core.QTimer = MagicMock
    core.QSize = MagicMock
    core.QDate = MagicMock
    core.QTime = MagicMock
    core.QEvent = MagicMock
    core.QPoint = MagicMock
    core.QPointF = MagicMock
    core.QRect = MagicMock
    core.QRectF = MagicMock
    core.QEasingCurve = MagicMock
    core.QPropertyAnimation = MagicMock
    core.QVariantAnimation = MagicMock

    widgets = MagicMock()
    gui = MagicMock()
    printers = MagicMock()

    pkg = MagicMock()
    pkg.QtCore = core
    pkg.QtWidgets = widgets
    pkg.QtGui = gui
    pkg.QtPrintSupport = printers

    sys.modules["PySide6"] = pkg
    sys.modules["PySide6.QtCore"] = core
    sys.modules["PySide6.QtWidgets"] = widgets
    sys.modules["PySide6.QtGui"] = gui
    sys.modules["PySide6.QtPrintSupport"] = printers
    print("[Web] PySide6 stubs installed for headless API boot")


install_pyside_stubs()
