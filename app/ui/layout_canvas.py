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
        self.drag_start_monitor_pos = None
        self.drag_start_mouse_pos = QPoint()
        self.drag_fixed_scale = None
        self.drag_base_bounds = None
        self.on_selection_changed = None

        self.canvas_padding = 32
        self.min_scale = 0.035
        self.max_scale = 0.24

        self.default_min_card_width = 88
        self.default_min_card_height = 58

        self.release_snap_distance_limit = 1200
        self.min_overlap_pixels = 120

        self.drag_expand_ratio = 0.04
        self.drag_min_expand_pixels = 24
        self.drag_max_expand_pixels = 72

        self.setMinimumHeight(460)
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
        friendly_name = monitor.get("friendly_name", "").strip()
        if friendly_name:
            return friendly_name
        return monitor["name"].replace("\\\\.\\", "")

    def _virtual_bounds(self):
        if not self.monitors:
            return 0, 0, 1, 1

        min_x = min(m["x"] for m in self.monitors)
        min_y = min(m["y"] for m in self.monitors)
        max_x = max(m["x"] + m["width"] for m in self.monitors)
        max_y = max(m["y"] + m["height"] for m in self.monitors)

        return min_x, min_y, max_x, max_y

    def _card_min_size(self):
        count = max(1, len(self.monitors))

        if count <= 2:
            return 120, 80
        if count == 3:
            return 96, 66
        if count == 4:
            return 82, 58

        return self.default_min_card_width, self.default_min_card_height

    def _compute_scale_and_offset_from_bounds(self, bounds):
        min_x, min_y, max_x, max_y = bounds

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

    def _soft_drag_bounds(self, current_bounds):
        if self.drag_base_bounds is None:
            return current_bounds

        base_min_x, base_min_y, base_max_x, base_max_y = self.drag_base_bounds
        cur_min_x, cur_min_y, cur_max_x, cur_max_y = current_bounds

        base_width = max(1, base_max_x - base_min_x)
        base_height = max(1, base_max_y - base_min_y)

        allow_x = int(base_width * self.drag_expand_ratio)
        allow_y = int(base_height * self.drag_expand_ratio)

        allow_x = max(self.drag_min_expand_pixels, min(allow_x, self.drag_max_expand_pixels))
        allow_y = max(self.drag_min_expand_pixels, min(allow_y, self.drag_max_expand_pixels))

        min_x = max(cur_min_x, base_min_x - allow_x)
        min_y = max(cur_min_y, base_min_y - allow_y)
        max_x = min(cur_max_x, base_max_x + allow_x)
        max_y = min(cur_max_y, base_max_y + allow_y)

        return min_x, min_y, max_x, max_y

    def _scale_and_offset(self):
        bounds = self._virtual_bounds()

        if self.dragging_monitor is not None:
            bounds = self._soft_drag_bounds(bounds)

        return self._compute_scale_and_offset_from_bounds(bounds)

    def monitor_rect(self, monitor):
        scale, offset_x, offset_y = self._scale_and_offset()
        min_w, min_h = self._card_min_size()

        x = int(monitor["x"] * scale + offset_x)
        y = int(monitor["y"] * scale + offset_y)
        w = max(min_w, int(monitor["width"] * scale))
        h = max(min_h, int(monitor["height"] * scale))

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

        if is_selected and not monitor.get("primary", False):
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

        friendly_name = monitor.get("friendly_name", "Unknown monitor")
        max_name_length = 24
        if len(friendly_name) > max_name_length:
            friendly_name = friendly_name[:max_name_length - 1] + "…"

        lines = [
            friendly_name,
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

    def _clamp_to_vertical_overlap(self, proposed_y, moving_monitor, target):
        min_overlap = min(
            self.min_overlap_pixels,
            moving_monitor["height"],
            target["height"],
        )

        min_y = target["y"] - moving_monitor["height"] + min_overlap
        max_y = target["y"] + target["height"] - min_overlap

        return int(max(min_y, min(proposed_y, max_y)))

    def _clamp_to_horizontal_overlap(self, proposed_x, moving_monitor, target):
        min_overlap = min(
            self.min_overlap_pixels,
            moving_monitor["width"],
            target["width"],
        )

        min_x = target["x"] - moving_monitor["width"] + min_overlap
        max_x = target["x"] + target["width"] - min_overlap

        return int(max(min_x, min(proposed_x, max_x)))

    def _best_snap_target(self, moving_monitor):
        others = [m for m in self.monitors if m["name"] != moving_monitor["name"]]
        if not others:
            return None

        current_x = moving_monitor["x"]
        current_y = moving_monitor["y"]

        best = None
        best_distance = None

        for target in others:
            candidates = [
                ("left", target["x"] - moving_monitor["width"], current_y, target),
                ("right", target["x"] + target["width"], current_y, target),
                ("top", current_x, target["y"] - moving_monitor["height"], target),
                ("bottom", current_x, target["y"] + target["height"], target),
            ]

            for side, candidate_x, candidate_y, candidate_target in candidates:
                if side in ("left", "right"):
                    candidate_y = self._clamp_to_vertical_overlap(
                        candidate_y,
                        moving_monitor,
                        candidate_target
                    )
                else:
                    candidate_x = self._clamp_to_horizontal_overlap(
                        candidate_x,
                        moving_monitor,
                        candidate_target
                    )

                distance = abs(current_x - candidate_x) + abs(current_y - candidate_y)

                if best_distance is None or distance < best_distance:
                    best_distance = distance
                    best = (candidate_x, candidate_y, candidate_target, side, distance)

        return best

    def _snap_monitor_to_nearest_side(self, moving_monitor):
        best = self._best_snap_target(moving_monitor)
        if best is None:
            return

        best_x, best_y, _target, _side, distance = best

        if distance > self.release_snap_distance_limit:
            return

        moving_monitor["x"] = int(best_x)
        moving_monitor["y"] = int(best_y)

    def _clamp_drag_position(self, monitor):
        others = [m for m in self.monitors if m["name"] != monitor["name"]]
        if not others or self.drag_start_monitor_pos is None:
            return

        min_other_x = min(m["x"] for m in others)
        max_other_x = max(m["x"] + m["width"] for m in others)
        min_other_y = min(m["y"] for m in others)
        max_other_y = max(m["y"] + m["height"] for m in others)

        count = len(self.monitors)

        if count <= 2:
            left_margin = max(int(monitor["width"] * 0.12), 36)
            right_margin = max(int(monitor["width"] * 0.07), 20)
            top_margin = max(int(monitor["height"] * 0.12), 36)
            bottom_margin = max(int(monitor["height"] * 0.12), 36)
        else:
            left_margin = max(int(monitor["width"] * 0.22), 64)
            right_margin = max(int(monitor["width"] * 0.06), 18)
            top_margin = max(int(monitor["height"] * 0.18), 56)
            bottom_margin = max(int(monitor["height"] * 0.18), 56)

        min_x = int(min_other_x - left_margin - monitor["width"])
        max_x = int(max_other_x + right_margin)
        min_y = int(min_other_y - top_margin - monitor["height"])
        max_y = int(max_other_y + bottom_margin)

        monitor["x"] = max(min_x, min(monitor["x"], max_x))
        monitor["y"] = max(min_y, min(monitor["y"], max_y))

    def mousePressEvent(self, event):
        for monitor in reversed(self.monitors):
            rect = self.monitor_rect(monitor)
            if rect.contains(event.pos()):
                self.selected_monitor = monitor
                self._notify_selection_changed()

                if monitor.get("primary", False):
                    self.dragging_monitor = None
                    self.drag_start_monitor_pos = None
                    self.drag_start_mouse_pos = QPoint()
                    self.drag_fixed_scale = None
                    self.drag_base_bounds = None
                    self.update()
                    return

                self.dragging_monitor = monitor
                self.drag_offset = event.pos() - rect.topLeft()
                self.drag_start_mouse_pos = event.pos()
                self.drag_start_monitor_pos = (monitor["x"], monitor["y"])
                self.drag_base_bounds = self._virtual_bounds()

                scale, _, _ = self._compute_scale_and_offset_from_bounds(self.drag_base_bounds)
                self.drag_fixed_scale = scale

                self.update()
                return

        self.selected_monitor = None
        self.dragging_monitor = None
        self.drag_start_monitor_pos = None
        self.drag_start_mouse_pos = QPoint()
        self.drag_fixed_scale = None
        self.drag_base_bounds = None
        self._notify_selection_changed()
        self.update()

    def mouseMoveEvent(self, event):
        if not self.dragging_monitor or self.drag_start_monitor_pos is None or not self.drag_fixed_scale:
            return

        delta_pixels = event.pos() - self.drag_start_mouse_pos

        delta_x_world = int(delta_pixels.x() / self.drag_fixed_scale)
        delta_y_world = int(delta_pixels.y() / self.drag_fixed_scale)

        start_x, start_y = self.drag_start_monitor_pos

        self.dragging_monitor["x"] = start_x + delta_x_world
        self.dragging_monitor["y"] = start_y + delta_y_world

        self._clamp_drag_position(self.dragging_monitor)

        self._notify_selection_changed()
        self.update()

    def mouseReleaseEvent(self, event):
        if self.dragging_monitor:
            self._snap_monitor_to_nearest_side(self.dragging_monitor)

        self.dragging_monitor = None
        self.drag_start_monitor_pos = None
        self.drag_start_mouse_pos = QPoint()
        self.drag_fixed_scale = None
        self.drag_base_bounds = None
        self._notify_selection_changed()
        self.update()