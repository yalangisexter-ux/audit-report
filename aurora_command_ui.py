"""
aurora_command_ui.py - High-Tech Executive Operations HUD (Aurora Command)
Recreates the cyber-HUD interface with:
- Top Metrics Strip with Glowing Neon Sparklines & Scenario Switcher
- Centerpiece Visual Enterprise Capital & Operations Flow Diagram (curved Bezier ribbons)
- Matrix Grid Table with Interactive Sliders and Toggle Switches
- Predictive Risk Engine with 6-Axis Concentric Spider/Radar Chart
- Talent Attrition Risk Heatmap (T1..T8 Grid)
- AI-Powered Recommendation Action Pills
"""

import math
from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from PySide6.QtGui import (
    QColor, QPainter, QPainterPath, QPen, QBrush, QFont,
    QLinearGradient, QRadialGradient, QCursor
)
from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QSlider, QTableWidget,
    QHeaderView, QSizePolicy, QToolTip
)


class NeonSparklineCard(QFrame):
    """Top-strip KPI card with real-time glowing bezier sparkline."""
    def __init__(self, title, value, color="#00F0FF", points=None, icon="↗", parent=None):
        super().__init__(parent)
        self.title_text = title
        self.value_text = value
        self.line_color = QColor(color)
        self.icon_text = icon
        self.points = points or [0.25, 0.40, 0.35, 0.65, 0.50, 0.70, 0.60, 0.90, 0.85, 1.0]
        self.setObjectName("sparklineCard")
        self.setMinimumHeight(84)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet("""
            QFrame#sparklineCard {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0D1424, stop:1 #080C14);
                border: 1.2px solid rgba(0, 240, 255, 0.22);
                border-radius: 12px;
            }
        """)

    def set_data(self, value, points=None):
        self.value_text = value
        if points:
            self.points = points
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w, h = self.width(), self.height()

        # Left Metric Text
        title_font = QFont("Segoe UI", 7, QFont.Weight.Bold)
        title_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.8)
        painter.setFont(title_font)
        painter.setPen(QColor("#94A3B8"))
        painter.drawText(QRectF(14, 12, w * 0.45, 16), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.title_text)

        val_font = QFont("Segoe UI", 16, QFont.Weight.Black)
        painter.setFont(val_font)
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(QRectF(14, 30, w * 0.45, 34), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.value_text)

        # Right Side Sparkline Curve
        spark_x = w * 0.42
        spark_w = w - spark_x - 16
        spark_y = 14
        spark_h = h - 28

        if len(self.points) >= 2 and spark_w > 20:
            step = spark_w / (len(self.points) - 1)
            coords = []
            for i, p in enumerate(self.points):
                cx = spark_x + i * step
                cy = spark_y + spark_h - (p * spark_h * 0.85)
                coords.append(QPointF(cx, cy))

            # Draw glowing gradient area fill under curve
            fill_path = QPainterPath()
            fill_path.moveTo(coords[0].x(), spark_y + spark_h)
            fill_path.lineTo(coords[0])

            # Cubic bezier curve connection
            for i in range(len(coords) - 1):
                p0 = coords[i]
                p1 = coords[i + 1]
                mid_x = (p0.x() + p1.x()) / 2.0
                fill_path.cubicTo(mid_x, p0.y(), mid_x, p1.y(), p1.x(), p1.y())

            fill_path.lineTo(coords[-1].x(), spark_y + spark_h)
            fill_path.closeSubpath()

            grad = QLinearGradient(0, spark_y, 0, spark_y + spark_h)
            grad.setColorAt(0.0, QColor(self.line_color.red(), self.line_color.green(), self.line_color.blue(), 70))
            grad.setColorAt(1.0, QColor(self.line_color.red(), self.line_color.green(), self.line_color.blue(), 0))
            painter.fillPath(fill_path, QBrush(grad))

            # Stroke the curve
            stroke_path = QPainterPath()
            stroke_path.moveTo(coords[0])
            for i in range(len(coords) - 1):
                p0 = coords[i]
                p1 = coords[i + 1]
                mid_x = (p0.x() + p1.x()) / 2.0
                stroke_path.cubicTo(mid_x, p0.y(), mid_x, p1.y(), p1.x(), p1.y())

            pen = QPen(self.line_color, 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.drawPath(stroke_path)

            # Glowing endpoint dot
            last_pt = coords[-1]
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(self.line_color.red(), self.line_color.green(), self.line_color.blue(), 100))
            painter.drawEllipse(last_pt, 6, 6)
            painter.setBrush(QColor("#FFFFFF"))
            painter.drawEllipse(last_pt, 2.5, 2.5)


class EnterpriseFlowWidget(QFrame):
    """
    Centerpiece: Enterprise Capital & Operations Diagram.
    Visual Sankey / Bezier Node Graph connecting:
    Source (Left) -> 4 Core Nodes (Middle) -> 3 Output Nodes (Right)
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("enterpriseFlowWidget")
        self.setMinimumHeight(300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setMouseTracking(True)
        self.hovered_node = None
        self.setStyleSheet("""
            QFrame#enterpriseFlowWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #090E1A, stop:1 #060912);
                border: 1.5px solid rgba(0, 240, 255, 0.25);
                border-radius: 14px;
            }
        """)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w, h = float(self.width()), float(self.height())

        # Header Title
        title_font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        painter.setFont(title_font)
        painter.setPen(QColor("#CBD5E1"))
        painter.drawText(QRectF(18, 14, 300, 20), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "Enterprise Capital Diagram")

        # Top Right Legend / Status
        stat_font = QFont("Segoe UI", 7, QFont.Weight.Bold)
        painter.setFont(stat_font)
        painter.setPen(QColor("#64748B"))
        painter.drawText(QRectF(w - 240, 14, 222, 20), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, "ROUTING: OPTIMIZED  •  FLOW: ACTIVE")

        # Geometry for 3 tiers
        stage_top = 46.0
        stage_h = h - stage_top - 16.0

        # Tier 1: Left Node
        n1_w = min(150.0, w * 0.16)
        n1_h = 60.0
        n1_x = 24.0
        n1_y = stage_top + (stage_h - n1_h) / 2.0
        n1_rect = QRectF(n1_x, n1_y, n1_w, n1_h)

        # Tier 2: 4 Middle Nodes
        n2_w = min(190.0, w * 0.22)
        n2_h = min(54.0, (stage_h - 36.0) / 4.0)
        n2_x = (w - n2_w) * 0.48
        n2_spacing = (stage_h - (4 * n2_h)) / 3.0
        n2_rects = []
        for i in range(4):
            y = stage_top + i * (n2_h + n2_spacing)
            n2_rects.append(QRectF(n2_x, y, n2_w, n2_h))

        # Tier 3: 3 Right Nodes
        n3_w = min(140.0, w * 0.16)
        n3_h = min(54.0, (stage_h - 24.0) / 3.0)
        n3_x = w - n3_w - 24.0
        n3_spacing = (stage_h - (3 * n3_h)) / 2.0
        n3_rects = []
        for i in range(3):
            y = stage_top + i * (n3_h + n3_spacing)
            n3_rects.append(QRectF(n3_x, y, n3_w, n3_h))

        # 1. Draw Flow Bezier Ribbons between Tier 1 and Tier 2
        p1_right = QPointF(n1_rect.right(), n1_rect.center().y())
        t2_colors = [
            QColor("#00F0FF"),  # Automated Payroll (Cyan)
            QColor("#10B981"),  # R&D Core (Emerald)
            QColor("#06B6D4"),  # Cloud infrastructure (Cyan/Blue)
            QColor("#818CF8"),  # Yield infrastructure (Indigo)
        ]

        for i, (r2, col) in enumerate(zip(n2_rects, t2_colors)):
            p2_left = QPointF(r2.left(), r2.center().y())
            ribbon = QPainterPath()
            thickness = max(8.0, n1_h * 0.16)
            y_offset = (i - 1.5) * (thickness * 0.9)

            src_top = QPointF(p1_right.x(), p1_right.y() + y_offset - thickness / 2.0)
            src_bot = QPointF(p1_right.x(), p1_right.y() + y_offset + thickness / 2.0)
            dst_top = QPointF(p2_left.x(), p2_left.y() - thickness / 2.0)
            dst_bot = QPointF(p2_left.x(), p2_left.y() + thickness / 2.0)

            c1_x = src_top.x() + (dst_top.x() - src_top.x()) * 0.5
            c2_x = src_top.x() + (dst_top.x() - src_top.x()) * 0.5

            ribbon.moveTo(src_top)
            ribbon.cubicTo(c1_x, src_top.y(), c2_x, dst_top.y(), dst_top.x(), dst_top.y())
            ribbon.lineTo(dst_bot)
            ribbon.cubicTo(c2_x, dst_bot.y(), c1_x, src_bot.y(), src_bot.x(), src_bot.y())
            ribbon.closeSubpath()

            # Glowing gradient
            grad = QLinearGradient(src_top, dst_top)
            grad.setColorAt(0.0, QColor(0, 240, 255, 90))
            grad.setColorAt(1.0, QColor(col.red(), col.green(), col.blue(), 85))
            painter.fillPath(ribbon, QBrush(grad))

            # Center neon line
            center_path = QPainterPath()
            center_path.moveTo(p1_right.x(), p1_right.y() + y_offset)
            center_path.cubicTo(c1_x, p1_right.y() + y_offset, c2_x, p2_left.y(), p2_left.x(), p2_left.y())
            painter.setPen(QPen(QColor(col.red(), col.green(), col.blue(), 140), 1.2))
            painter.drawPath(center_path)

        # 2. Draw Flow Bezier Ribbons between Tier 2 and Tier 3
        # Connect T2 nodes to T3 nodes in glowing overlapping curves
        t2_to_t3_links = [
            (0, 0, QColor("#A855F7")),
            (0, 1, QColor("#00F0FF")),
            (1, 1, QColor("#10B981")),
            (1, 2, QColor("#A855F7")),
            (2, 1, QColor("#06B6D4")),
            (3, 2, QColor("#C084FC")),
        ]

        for s_idx, d_idx, col in t2_to_t3_links:
            r_src = n2_rects[s_idx]
            r_dst = n3_rects[d_idx]
            p_src = QPointF(r_src.right(), r_src.center().y())
            p_dst = QPointF(r_dst.left(), r_dst.center().y())

            ribbon = QPainterPath()
            th = 6.0
            s_top = QPointF(p_src.x(), p_src.y() - th / 2.0)
            s_bot = QPointF(p_src.x(), p_src.y() + th / 2.0)
            d_top = QPointF(p_dst.x(), p_dst.y() - th / 2.0)
            d_bot = QPointF(p_dst.x(), p_dst.y() + th / 2.0)

            cx = p_src.x() + (p_dst.x() - p_src.x()) * 0.5
            ribbon.moveTo(s_top)
            ribbon.cubicTo(cx, s_top.y(), cx, d_top.y(), d_top.x(), d_top.y())
            ribbon.lineTo(d_bot)
            ribbon.cubicTo(cx, d_bot.y(), cx, s_bot.y(), s_bot.x(), s_bot.y())
            ribbon.closeSubpath()

            grad = QLinearGradient(s_top, d_top)
            grad.setColorAt(0.0, QColor(col.red(), col.green(), col.blue(), 40))
            grad.setColorAt(1.0, QColor(col.red(), col.green(), col.blue(), 85))
            painter.fillPath(ribbon, QBrush(grad))

        # 3. Draw Nodes (Cards)
        # Helper to draw a sleek cyber node
        def draw_node(rect, title, val, border_color, sub=""):
            painter.setPen(QPen(border_color, 1.4))
            painter.setBrush(QColor(13, 19, 34, 230))
            painter.drawRoundedRect(rect, 8, 8)

            # Node label
            f_title = QFont("Segoe UI", 7, QFont.Weight.Bold)
            painter.setFont(f_title)
            painter.setPen(QColor("#FFFFFF"))
            painter.drawText(QRectF(rect.x() + 8, rect.y() + 6, rect.width() - 16, 14), Qt.AlignmentFlag.AlignLeft, title)

            if sub:
                f_sub = QFont("Segoe UI", 6, QFont.Weight.Medium)
                painter.setFont(f_sub)
                painter.setPen(QColor("#94A3B8"))
                painter.drawText(QRectF(rect.x() + 8, rect.y() + 20, rect.width() - 16, 12), Qt.AlignmentFlag.AlignLeft, sub)

            f_val = QFont("Segoe UI", 8, QFont.Weight.Black)
            painter.setFont(f_val)
            painter.setPen(border_color)
            val_y = rect.y() + (32 if sub else 22)
            painter.drawText(QRectF(rect.x() + 8, val_y, rect.width() - 16, 16), Qt.AlignmentFlag.AlignLeft, val)

            # Draw glowing play indicator badge on right
            ind_x = rect.right() - 14
            ind_y = rect.center().y()
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(border_color)
            painter.drawEllipse(QPointF(ind_x, ind_y), 3.5, 3.5)

        # Draw Tier 1 Node
        draw_node(n1_rect, "Revenue Streams", "$428.4M", QColor("#00F0FF"))

        # Draw Tier 2 Nodes
        t2_specs = [
            ("Automated Payroll", "$3900k", QColor("#A855F7"), ""),
            ("R&D Core", "$428.4M - $2280k", QColor("#10B981"), "Transactions/all data"),
            ("Cloud infrastructure", "$300k - $180k", QColor("#00F0FF"), ""),
            ("Yield infrastructure", "$200k - $1200k", QColor("#818CF8"), ""),
        ]
        for r, (t, v, c, s) in zip(n2_rects, t2_specs):
            draw_node(r, t, v, c, s)

        # Draw Tier 3 Nodes
        t3_specs = [
            ("Revenue Streams", "$428.4M", QColor("#A855F7")),
            ("R&D Core", "$2394k", QColor("#10B981")),
            ("Yield Returns", "$1350k", QColor("#C084FC")),
        ]
        for r, (t, v, c) in zip(n3_rects, t3_specs):
            draw_node(r, t, v, c)


class MatrixGridWidget(QFrame):
    """
    Bottom Matrix Grid table with:
    - Department name
    - Headcounts
    - Burn Rate
    - Capital Efficiency Ratio
    - Interactive Toggle Switches
    - Real-Time Budget Reallocation Sliders (glowing cyan thumbs)
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("matrixGridPanel")
        self.setStyleSheet("""
            QFrame#matrixGridPanel {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0D1322, stop:1 #080C14);
                border: 1.2px solid rgba(0, 240, 255, 0.20);
                border-radius: 12px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        # Header Row
        header_row = QHBoxLayout()
        title = QLabel("Matrix Grid")
        title.setStyleSheet("font-size: 10.5pt; font-weight: 800; color: #FFFFFF; letter-spacing: 0.5px;")
        header_row.addWidget(title)
        header_row.addStretch(1)

        freq_label = QLabel("Frequency updated:")
        freq_label.setStyleSheet("color: #94A3B8; font-size: 8pt; font-weight: 600;")
        header_row.addWidget(freq_label)

        self.freq_combo = QComboBox()
        self.freq_combo.addItems(["Department date", "Daily EOD sync", "Real-Time 15s"])
        self.freq_combo.setStyleSheet("""
            QComboBox {
                background: #090E1A; color: #E2E8F0;
                border: 1px solid rgba(0, 240, 255, 0.30);
                border-radius: 6px; padding: 3px 10px; font-size: 8pt; font-weight: 600;
            }
        """)
        header_row.addWidget(self.freq_combo)
        layout.addLayout(header_row)

        # Table Widget
        self.table = QTableWidget(7, 6)
        self.table.setHorizontalHeaderLabels([
            "Department", "Headcounts", "Burn Rate", "Capital Efficiency Ratio", "Toggle", "Real-Time Budget Realloc..."
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setStyleSheet("""
            QTableWidget {
                background: transparent;
                border: 0;
                gridline-color: transparent;
                color: #F8FAFC;
                font-size: 8.5pt;
            }
            QHeaderView::section {
                background: #070B14;
                color: #94A3B8;
                border: 0;
                border-bottom: 1.5px solid rgba(0, 240, 255, 0.25);
                font-size: 7.5pt;
                font-weight: 700;
                text-transform: uppercase;
                padding: 6px 8px;
            }
        """)

        # Rows data from Image 3
        rows_data = [
            ("Engineering", "230", "$488", "4.87%", True, 50),
            ("Marketing", "100", "$160k", "2.89%", True, 20),
            ("Sales", "130", "$488", "2.35%", True, 25),
            ("Operations", "100", "$350k", "2.89%", True, 90),
            ("Enginering Core", "100", "$458", "3.99%", True, 20),
            ("Managing", "90", "$100k", "4.39%", True, 30),
            ("Operations Desk", "70", "$488", "1.39%", True, 15),
        ]

        self.table.verticalHeader().setDefaultSectionSize(36)
        self.sliders = []

        for row_idx, (dept, hc, burn, eff, toggle_val, pct) in enumerate(rows_data):
            # Dept
            dept_lbl = QLabel(f" {dept}")
            dept_lbl.setStyleSheet("color: #FFFFFF; font-weight: 600;")
            self.table.setCellWidget(row_idx, 0, dept_lbl)

            # Headcounts
            hc_lbl = QLabel(hc)
            hc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hc_lbl.setStyleSheet("color: #CBD5E1; font-weight: 600;")
            self.table.setCellWidget(row_idx, 1, hc_lbl)

            # Burn Rate
            burn_lbl = QLabel(burn)
            burn_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            burn_lbl.setStyleSheet("color: #CBD5E1; font-weight: 600;")
            self.table.setCellWidget(row_idx, 2, burn_lbl)

            # Capital Efficiency
            eff_lbl = QLabel(eff)
            eff_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            eff_lbl.setStyleSheet("color: #38BDF8; font-weight: 700;")
            self.table.setCellWidget(row_idx, 3, eff_lbl)

            # Toggle Switch Pill
            toggle_btn = QPushButton("● ON" if toggle_val else "○ OFF")
            toggle_btn.setCheckable(True)
            toggle_btn.setChecked(toggle_val)
            toggle_btn.setFixedSize(56, 24)
            toggle_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(0, 240, 255, 0.15);
                    color: #00F0FF;
                    border: 1px solid #00F0FF;
                    border-radius: 12px;
                    font-size: 7pt; font-weight: 800;
                }
                QPushButton:!checked {
                    background: rgba(255, 255, 255, 0.05);
                    color: #64748B;
                    border: 1px solid #475569;
                }
            """)
            toggle_btn.toggled.connect(lambda chk, b=toggle_btn: b.setText("● ON" if chk else "○ OFF"))
            t_container = QWidget()
            t_layout = QHBoxLayout(t_container)
            t_layout.setContentsMargins(0, 0, 0, 0)
            t_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            t_layout.addWidget(toggle_btn)
            self.table.setCellWidget(row_idx, 4, t_container)

            # Real-Time Budget Reallocation Slider
            slider_container = QWidget()
            s_layout = QHBoxLayout(slider_container)
            s_layout.setContentsMargins(6, 0, 8, 0)
            s_layout.setSpacing(8)

            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, 100)
            slider.setValue(pct)
            slider.setStyleSheet("""
                QSlider::groove:horizontal {
                    background: rgba(255, 255, 255, 0.12);
                    height: 5px; border-radius: 2px;
                }
                QSlider::sub-page:horizontal {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00F0FF, stop:1 #3B82F6);
                    height: 5px; border-radius: 2px;
                }
                QSlider::handle:horizontal {
                    background: #FFFFFF;
                    border: 2px solid #00F0FF;
                    width: 14px; height: 14px; margin: -5px 0;
                    border-radius: 7px;
                }
                QSlider::handle:horizontal:hover {
                    background: #00F0FF;
                    border-color: #FFFFFF;
                }
            """)

            val_display = QLabel(f"{pct}%")
            val_display.setFixedWidth(34)
            val_display.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            val_display.setStyleSheet("color: #00F0FF; font-weight: 800; font-size: 8pt;")

            slider.valueChanged.connect(lambda v, lbl=val_display: lbl.setText(f"{v}%"))
            s_layout.addWidget(slider, 1)
            s_layout.addWidget(val_display)
            self.table.setCellWidget(row_idx, 5, slider_container)
            self.sliders.append(slider)

        layout.addWidget(self.table)


class RadarRiskWidget(QFrame):
    """
    Anomaly & Predictive Risk Engine (Concentric Spider / Radar Chart).
    6-Axes Polygon measuring Market Volatility, Operational Risk, Talent Retention, etc.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("radarRiskWidget")
        self.setMinimumHeight(180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("""
            QFrame#radarRiskWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0D1322, stop:1 #080C14);
                border: 1.2px solid rgba(0, 240, 255, 0.20);
                border-radius: 12px;
            }
        """)
        self.axes = [
            "Market\nVolatility",
            "Operational\nRisk",
            "Talent\nRetention",
            "Compliance\nRisk",
            "Facility\nCapacity",
            "Cash\nRunway"
        ]
        self.values = [0.72, 0.45, 0.85, 0.40, 0.55, 0.65]

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w, h = float(self.width()), float(self.height())

        # Header Title
        title_font = QFont("Segoe UI", 8, QFont.Weight.Bold)
        painter.setFont(title_font)
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(QRectF(12, 10, w - 24, 18), Qt.AlignmentFlag.AlignLeft, "Anomaly & Predictive Risk Engine")

        # Center and Radius
        cx = w / 2.0
        cy = (h + 16.0) / 2.0
        radius = min(cx - 38.0, cy - 28.0, 68.0)
        if radius < 20.0:
            return

        num_axes = len(self.axes)
        angles = [math.radians(i * 360.0 / num_axes - 90.0) for i in range(num_axes)]

        # Draw 4 Concentric Polygon Rings
        for tier in (0.25, 0.50, 0.75, 1.0):
            r_tier = radius * tier
            ring_path = QPainterPath()
            for idx, a in enumerate(angles):
                px = cx + r_tier * math.cos(a)
                py = cy + r_tier * math.sin(a)
                if idx == 0:
                    ring_path.moveTo(px, py)
                else:
                    ring_path.lineTo(px, py)
            ring_path.closeSubpath()
            painter.setPen(QPen(QColor(255, 255, 255, 25), 1, Qt.PenStyle.DashLine))
            painter.drawPath(ring_path)

        # Draw Axis Lines & Small Labels
        lbl_font = QFont("Segoe UI", 6, QFont.Weight.DemiBold)
        painter.setFont(lbl_font)
        for i, (a, label) in enumerate(zip(angles, self.axes)):
            ax = cx + radius * math.cos(a)
            ay = cy + radius * math.sin(a)
            painter.setPen(QPen(QColor(255, 255, 255, 35), 1))
            painter.drawLine(QPointF(cx, cy), QPointF(ax, ay))

            # Label positioned outside
            lx = cx + (radius + 18.0) * math.cos(a)
            ly = cy + (radius + 18.0) * math.sin(a)
            painter.setPen(QColor("#94A3B8"))
            lbl_rect = QRectF(lx - 28.0, ly - 10.0, 56.0, 20.0)
            painter.drawText(lbl_rect, Qt.AlignmentFlag.AlignCenter, label.split("\n")[0])

        # Draw Data Polygon
        data_path = QPainterPath()
        data_pts = []
        for i, (a, val) in enumerate(zip(angles, self.values)):
            r_val = radius * val
            px = cx + r_val * math.cos(a)
            py = cy + r_val * math.sin(a)
            pt = QPointF(px, py)
            data_pts.append(pt)
            if i == 0:
                data_path.moveTo(pt)
            else:
                data_path.lineTo(pt)
        data_path.closeSubpath()

        # Translucent Cyan Gradient Fill
        painter.fillPath(data_path, QBrush(QColor(0, 240, 255, 55)))

        # Neon Cyan Stroke
        painter.setPen(QPen(QColor("#00F0FF"), 2.0, Qt.PenStyle.SolidLine))
        painter.drawPath(data_path)

        # Draw Vertices
        for pt in data_pts:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 240, 255, 120))
            painter.drawEllipse(pt, 4.5, 4.5)
            painter.setBrush(QColor("#FFFFFF"))
            painter.drawEllipse(pt, 2.0, 2.0)


class HeatmapRiskWidget(QFrame):
    """
    Talent Attrition Risk Heatmap (Grid of Green/Amber/Red blocks).
    Matches Image 3's grid layout.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("heatmapRiskWidget")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet("""
            QFrame#heatmapRiskWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0D1322, stop:1 #080C14);
                border: 1.2px solid rgba(0, 240, 255, 0.20);
                border-radius: 12px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Header Row
        h_row = QHBoxLayout()
        title = QLabel("Talent Attrition Risk Heatmap")
        title.setStyleSheet("font-size: 8pt; font-weight: 700; color: #FFFFFF;")
        h_row.addWidget(title)
        h_row.addStretch(1)

        # Legend
        legend = QLabel("■ Risk  ■ Risk  ■ Safe")
        legend.setStyleSheet("color: #EF4444; font-size: 7pt; font-weight: 700;")
        h_row.addWidget(legend)
        layout.addLayout(h_row)

        # Grid of Tiles (4 Rows x 8 Columns)
        # 1=Green (Safe), 2=Amber (Moderate), 3=Red (Risk)
        grid_data = [
            ("Team",  [2, 3, 2, 3, 3, 3, 3, 3]),
            ("Team",  [1, 2, 2, 2, 3, 3, 3, 3]),
            ("Sales", [1, 1, 2, 2, 3, 3, 2, 2]),
            ("Ops",   [1, 1, 1, 2, 2, 2, 2, 2]),
        ]

        grid = QGridLayout()
        grid.setSpacing(4)
        grid.setContentsMargins(0, 4, 0, 0)

        # Header Col labels (T1..T8)
        for c in range(8):
            t_lbl = QLabel(f"T{c+1}")
            t_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            t_lbl.setStyleSheet("color: #64748B; font-size: 6.5pt; font-weight: 700;")
            grid.addWidget(t_lbl, 0, c + 1)

        colors = {
            1: "#10B981",  # Green
            2: "#F59E0B",  # Amber
            3: "#EF4444",  # Red
        }

        for r_idx, (name, row_vals) in enumerate(grid_data):
            row_lbl = QLabel(name)
            row_lbl.setStyleSheet("color: #94A3B8; font-size: 7pt; font-weight: 600;")
            grid.addWidget(row_lbl, r_idx + 1, 0)

            for c_idx, val in enumerate(row_vals):
                tile = QFrame()
                c_hex = colors.get(val, "#10B981")
                tile.setStyleSheet(f"""
                    QFrame {{
                        background: {c_hex};
                        border-radius: 4px;
                        min-width: 18px; max-width: 28px;
                        min-height: 14px; max-height: 18px;
                    }}
                """)
                grid.addWidget(tile, r_idx + 1, c_idx + 1)

        layout.addLayout(grid)


class ActionPillsWidget(QFrame):
    """
    AI-powered Recommendation Action Pills.
    Matches Image 3's interactive recommendation buttons.
    """
    actionTriggered = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("actionPillsWidget")
        self.setStyleSheet("""
            QFrame#actionPillsWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0D1322, stop:1 #080C14);
                border: 1.2px solid rgba(0, 240, 255, 0.20);
                border-radius: 12px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        title = QLabel("AI-powered Recommendation Action pills")
        title.setStyleSheet("font-size: 8pt; font-weight: 700; color: #FFFFFF;")
        layout.addWidget(title)

        pills = [
            "[Rebalance Q3 Cloud Reserve +$240k]",
            "[Accelerate R&D Hiring: 12 FTEs]",
            "[Audit Athlete Compliance: 100% Verified]",
        ]

        for p_text in pills:
            btn = QPushButton(p_text)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(0, 240, 255, 0.08);
                    color: #00F0FF;
                    border: 1px solid rgba(0, 240, 255, 0.35);
                    border-radius: 7px;
                    padding: 5px 10px;
                    font-size: 7.5pt;
                    font-weight: 700;
                    text-align: left;
                }
                QPushButton:hover {
                    background: rgba(0, 240, 255, 0.22);
                    border-color: #00F0FF;
                    color: #FFFFFF;
                }
                QPushButton:pressed {
                    background: rgba(0, 240, 255, 0.35);
                }
            """)
            btn.clicked.connect(lambda chk=False, t=p_text: self.actionTriggered.emit(t))
            layout.addWidget(btn)


class AuroraCommandHUD(QWidget):
    """
    Complete Executive Operations HUD assembling:
    - Top Strip: 2 Neon Sparklines, Scenario Selector, Notification Bell, User Avatar
    - Centerpiece: Visual Enterprise Flow Diagram
    - Bottom Split: Left Matrix Grid + Right Intelligence Panel
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("auroraCommandHUD")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(12)

        # 1. Top Strip: KPI Sparklines + Scenario Switcher + Actions
        top_strip = QHBoxLayout()
        top_strip.setSpacing(10)

        # Metric 1: Global Liquidity (Cyan Sparkline)
        self.kpi_liquidity = NeonSparklineCard(
            "GLOBAL LIQUIDITY:", "$428.4M", color="#00F0FF",
            points=[0.3, 0.45, 0.35, 0.65, 0.50, 0.85, 0.70, 0.95, 0.80, 1.0]
        )
        top_strip.addWidget(self.kpi_liquidity, 2)

        # Metric 2: Enterprise Valuation (Emerald Sparkline)
        self.kpi_valuation = NeonSparklineCard(
            "ENTERPRISE VALUATION:", "$2.14B", color="#10B981",
            points=[0.2, 0.35, 0.45, 0.55, 0.50, 0.75, 0.80, 0.90, 0.95, 1.0]
        )
        top_strip.addWidget(self.kpi_valuation, 2)

        # Scenario Switch Card
        scenario_card = QFrame()
        scenario_card.setObjectName("scenarioCard")
        scenario_card.setStyleSheet("""
            QFrame#scenarioCard {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0D1424, stop:1 #080C14);
                border: 1.2px solid rgba(0, 240, 255, 0.22);
                border-radius: 12px;
                padding: 6px 12px;
            }
        """)
        scen_layout = QVBoxLayout(scenario_card)
        scen_layout.setContentsMargins(8, 6, 8, 6)
        scen_layout.setSpacing(4)
        scen_lbl = QLabel("SCENARIO SWITCH:")
        scen_lbl.setStyleSheet("color: #94A3B8; font-size: 7pt; font-weight: 700; letter-spacing: 0.8px;")
        scen_layout.addWidget(scen_lbl)

        self.scenario_combo = QComboBox()
        self.scenario_combo.addItems([
            "Aggressive Growth [ACTIVE]",
            "Base Case Baseline",
            "Recession Stress Test",
            "Peak Season Scaled"
        ])
        self.scenario_combo.setStyleSheet("""
            QComboBox {
                background: #090E1A; color: #00F0FF;
                border: 1.5px solid #00F0FF;
                border-radius: 7px; padding: 4px 10px; font-size: 8.5pt; font-weight: 700;
            }
        """)
        scen_layout.addWidget(self.scenario_combo)
        top_strip.addWidget(scenario_card, 2)

        # Quick Utility Strip: Notification Button + Avatar
        util_layout = QVBoxLayout()
        util_layout.setSpacing(6)

        notif_btn = QPushButton("🔔  Interactive Notification")
        notif_btn.setStyleSheet("""
            QPushButton {
                background: rgba(239, 68, 68, 0.12);
                color: #F8FAFC;
                border: 1px solid rgba(239, 68, 68, 0.40);
                border-radius: 8px; padding: 6px 14px;
                font-size: 8pt; font-weight: 700;
            }
            QPushButton:hover {
                background: rgba(239, 68, 68, 0.25);
                border-color: #EF4444;
            }
        """)
        util_layout.addWidget(notif_btn)

        trends_chip = QLabel("📈 Short-term Trends  [KPI: ACTIVE]")
        trends_chip.setStyleSheet("""
            background: rgba(0, 240, 255, 0.10);
            color: #00F0FF;
            border: 1px solid rgba(0, 240, 255, 0.30);
            border-radius: 6px; padding: 3px 8px;
            font-size: 7pt; font-weight: 700;
        """)
        util_layout.addWidget(trends_chip)
        top_strip.addLayout(util_layout, 1)

        main_layout.addLayout(top_strip)

        # 2. Centerpiece: Visual Enterprise Flow Diagram
        self.flow_widget = EnterpriseFlowWidget()
        main_layout.addWidget(self.flow_widget)

        # 3. Bottom Row: Matrix Grid (Left) + Right Intelligence Panel (Right)
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(12)

        # Left: Matrix Grid Table
        self.matrix_grid = MatrixGridWidget()
        bottom_row.addWidget(self.matrix_grid, 6)

        # Right: Intelligence Panel (Radar + Heatmap + Pills)
        intel_panel = QVBoxLayout()
        intel_panel.setSpacing(10)

        self.radar_widget = RadarRiskWidget()
        intel_panel.addWidget(self.radar_widget, 1)

        self.heatmap_widget = HeatmapRiskWidget()
        intel_panel.addWidget(self.heatmap_widget)

        self.action_pills = ActionPillsWidget()
        intel_panel.addWidget(self.action_pills)

        bottom_row.addLayout(intel_panel, 4)
        main_layout.addLayout(bottom_row)
