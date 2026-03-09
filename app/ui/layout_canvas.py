from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from app.core.discovery import get_monitors


class LayoutCanvas(QWidget):
    def __init__(self):
        super().__init__()

        self.monitors = []
        self.selected_monitor = None
        self.dragging_monitor = None
        self.drag_offset = QPoint()
        self.on_selection_changed = None

        self.canvas_padding = 40
        self.min_scale = 0.08
        self.max_scale = 0.22

        self.setMinimumHeight(420)
        self.setMouseTracking(True)

        self.refresh_monitors()

    def refresh_monitors(self):
        self.monitors = get_monitors()

        if self.selected_monitor is not None:
            selected_name = self.selected_monitor["name"]
            self.selected_monitor = next(
                (m for m in self.monitors if m["name"] == selected_name),
                None
            )

        self._notify_selection_changed()
        self.update()

    def set_monitors(self, monitors):
        self.monitors = monitors

        if self.selected_monitor is not None:
            selected_name = self.selected_monitor["name"]
            self.selected_monitor = next(
                (m for m in self.monitors if m["name"] == selected_name),
                None
            )

        self._notify_selection_changed()
        self.update()

    def get_selected_monitor(self):
        return self.selected_monitor

    def set_selected_as_primary(self):
        if not self.selected_monitor:
            return

        target_name = self.selected_monitor["name"]
        target = next((m for m in self.monitors if m["name"] == target_name), None)
        if target is None:
            return

        offset_x = target["x"]
        offset_y = target["y"]

        for monitor in self.monitors:
            monitor["x"] -= offset_x
            monitor["y"] -= offset_y
            monitor["primary"] = monitor["name"] == target_name

        self.selected_monitor = target
        self._notify_selection_changed()
        self.update()

    def _notify_selection_changed(self):
        if self.on_selection_changed:
            self.on_selection_changed()

    @staticmethod
    def _display_label(monitor):
        return monitor["name"].replace("\\\\.\\", "")

    def _virtual_bounds(self):
        if not self.monitors:
            return 0, 0, 1, 1

        min_x = min(m["x"] for m in self.monitors)
        min_y = min(m["y"] for m in self.monitors)
        max_x = max(m["x"] + m["width"] for m in self.monitors)
        max_y = max(m["y"] + m["height"] for m in self.monitors)

        return min_x, min_y, max_x, max_y

    def _scale_and_offset(self):
        min_x, min_y, max_x, max_y = self._virtual_bounds()

        virtual_width = max(1, max_x - min_x)
        virtual_height = max(1, max_y - min_y)

        available_width = max(1, self.width() - self.canvas_padding * 2)
        available_height = max(1, self.height() - self.canvas_padding * 2)

        scale_x = available_width / virtual_width
        scale_y = available_height / virtual_height
        scale = max(self.min_scale, min(self.max_scale, min(scale_x, scale_y)))

        content_width = virtual_width * scale
        content_height = virtual_height * scale

        offset_x = (self.width() - content_width) / 2 - min_x * scale
        offset_y = (self.height() - content_height) / 2 - min_y * scale

        return scale, offset_x, offset_y

    def monitor_rect(self, monitor):
        scale, offset_x, offset_y = self._scale_and_offset()

        x = int(monitor["x"] * scale + offset_x)
        y = int(monitor["y"] * scale + offset_y)
        w = max(120, int(monitor["width"] * scale))
        h = max(80, int(monitor["height"] * scale))

        return QRect(x, y, w, h)

    def _draw_background(self, painter):
        painter.fillRect(self.rect(), QColor("#F8FAFC"))

        grid_pen = QPen(QColor("#EEF2F7"))
        grid_pen.setWidth(1)
        painter.setPen(grid_pen)

        step = 28
        for x in range(0, self.width(), step):
            painter.drawLine(x, 0, x, self.height())

        for y in range(0, self.height(), step):
            painter.drawLine(0, y, self.width(), y)

    def _draw_monitor_card(self, painter, monitor):
        rect = self.monitor_rect(monitor)

        is_selected = (
            self.selected_monitor is not None
            and self.selected_monitor["name"] == monitor["name"]
        )

        if monitor.get("primary", False):
            fill_color = QColor("#DBEAFE")
            border_color = QColor("#2563EB")
        else:
            fill_color = QColor("#FFFFFF")
            border_color = QColor("#CBD5E1")

        if is_selected:
            border_color = QColor("#0F172A")

        painter.setPen(QPen(border_color, 2))
        painter.setBrush(fill_color)
        painter.drawRoundedRect(rect, 14, 14)

        inner = rect.adjusted(14, 12, -14, -12)

        title_font = QFont("Segoe UI", 10)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(QColor("#0F172A"))
        painter.drawText(
            QRect(inner.left(), inner.top(), inner.width(), 22),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self._display_label(monitor)
        )

        if monitor.get("primary", False):
            badge_text = "PRIMARY"
            badge_rect = QRect(inner.right() - 82, inner.top(), 82, 24)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#2563EB"))
            painter.drawRoundedRect(badge_rect, 12, 12)

            badge_font = QFont("Segoe UI", 8)
            badge_font.setBold(True)
            painter.setFont(badge_font)
            painter.setPen(QColor("#FFFFFF"))
            painter.drawText(
                badge_rect,
                Qt.AlignmentFlag.AlignCenter,
                badge_text
            )

        painter.setPen(QColor("#475569"))
        body_font = QFont("Segoe UI", 9)
        painter.setFont(body_font)

        lines = [
            monitor.get("friendly_name", "Unknown monitor"),
            f'{monitor["width"]} × {monitor["height"]}',
            f'({monitor["x"]}, {monitor["y"]})'
        ]

        line_y = inner.top() + 34
        for line in lines:
            painter.drawText(
                QRect(inner.left(), line_y, inner.width(), 20),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                line
            )
            line_y += 22

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        self._draw_background(painter)

        for monitor in self.monitors:
            self._draw_monitor_card(painter, monitor)

    def _snap_monitor_to_nearest_side(self, moving_monitor):
        others = [m for m in self.monitors if m["name"] != moving_monitor["name"]]
        if not others:
            return

        best_target = None
        best_distance = None

        current_x = moving_monitor["x"]
        current_y = moving_monitor["y"]

        for target in others:
            left_x = target["x"] - moving_monitor["width"]
            right_x = target["x"] + target["width"]
            top_y = target["y"] - moving_monitor["height"]
            bottom_y = target["y"] + target["height"]

            candidates = [
                ("left", left_x, target["y"]),
                ("right", right_x, target["y"]),
                ("top", target["x"], top_y),
                ("bottom", target["x"], bottom_y),
            ]

            for side, cx, cy in candidates:
                dist = abs(current_x - cx) + abs(current_y - cy)
                if best_distance is None or dist < best_distance:
                    best_distance = dist
                    best_target = (side, cx, cy, target)

        if best_target is None:
            return

        side, best_x, best_y, target = best_target

        if side in ("left", "right"):
            if abs(current_y - target["y"]) < 140:
                best_y = target["y"]

        if side in ("top", "bottom"):
            if abs(current_x - target["x"]) < 140:
                best_x = target["x"]

        moving_monitor["x"] = int(best_x)
        moving_monitor["y"] = int(best_y)

    def mousePressEvent(self, event):
        for monitor in reversed(self.monitors):
            rect = self.monitor_rect(monitor)
            if rect.contains(event.pos()):
                self.selected_monitor = monitor
                self.dragging_monitor = monitor
                self.drag_offset = event.pos() - rect.topLeft()
                self._notify_selection_changed()
                self.update()
                return

        self.selected_monitor = None
        self.dragging_monitor = None
        self._notify_selection_changed()
        self.update()

    def mouseMoveEvent(self, event):
        if not self.dragging_monitor:
            return

        scale, offset_x, offset_y = self._scale_and_offset()

        new_x_pixels = event.pos().x() - self.drag_offset.x()
        new_y_pixels = event.pos().y() - self.drag_offset.y()

        self.dragging_monitor["x"] = int((new_x_pixels - offset_x) / scale)
        self.dragging_monitor["y"] = int((new_y_pixels - offset_y) / scale)

        self._notify_selection_changed()
        self.update()

    def mouseReleaseEvent(self, event):
        if self.dragging_monitor:
            self._snap_monitor_to_nearest_side(self.dragging_monitor)

        self.dragging_monitor = None
        self._notify_selection_changed()
        self.update()