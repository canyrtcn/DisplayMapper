import os
import sys

if "--agent-once" in sys.argv:
    from app.agent_once import run_agent_once
    run_agent_once()
    raise SystemExit(0)

if "--agent-watch" in sys.argv:
    from app.agent_watch import run_agent_watch
    run_agent_watch()
    raise SystemExit(0)

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.apply_engine import apply_layout
from app.core.profiles import (
    DEFAULT_PROFILE_PATH,
    apply_profile_to_monitors,
    load_profile,
    save_profile,
)
from app.core.startup import (
    disable_startup_agent,
    enable_startup_agent,
    is_startup_agent_enabled,
)
from app.ui.layout_canvas import LayoutCanvas


def resource_path(relative_path: str) -> str:
    base_path = getattr(sys, "_MEIPASS", None)
    if base_path:
        return os.path.join(base_path, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("DisplayMapper")
        self.setWindowIcon(QIcon(resource_path("DisplayMapper.ico")))
        self.setMinimumSize(1280, 820)

        self.canvas = LayoutCanvas()
        self.canvas.on_selection_changed = self.update_selection_panel

        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("StatusLabel")

        self.selection_title = QLabel("Selected monitor")
        self.selection_title.setObjectName("SectionTitle")

        self.selection_details = QLabel("No monitor selected")
        self.selection_details.setWordWrap(True)
        self.selection_details.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        self.selection_details.setObjectName("SelectionDetails")

        self.refresh_button = QPushButton("Refresh Layout")
        self.refresh_button.setObjectName("NeutralButton")
        self.refresh_button.clicked.connect(self.on_refresh_clicked)

        self.save_button = QPushButton("Save Profile")
        self.save_button.setObjectName("SuccessButton")
        self.save_button.clicked.connect(self.on_save_profile_clicked)

        self.load_button = QPushButton("Load Profile")
        self.load_button.setObjectName("NeutralButton")
        self.load_button.clicked.connect(self.on_load_profile_clicked)

        self.load_apply_button = QPushButton("Load + Apply Profile")
        self.load_apply_button.setObjectName("AccentButton")
        self.load_apply_button.clicked.connect(self.on_load_apply_profile_clicked)

        self.primary_button = QPushButton("Set as Primary")
        self.primary_button.setObjectName("WarningButton")
        self.primary_button.clicked.connect(self.on_set_primary_clicked)

        self.enable_startup_button = QPushButton("Enable Startup Agent")
        self.enable_startup_button.setObjectName("SuccessButton")
        self.enable_startup_button.clicked.connect(self.on_enable_startup_clicked)

        self.disable_startup_button = QPushButton("Disable Startup Agent")
        self.disable_startup_button.setObjectName("DangerButton")
        self.disable_startup_button.clicked.connect(self.on_disable_startup_clicked)

        self.apply_button = QPushButton("Apply Layout")
        self.apply_button.setObjectName("PrimaryButton")
        self.apply_button.clicked.connect(self.on_apply_clicked)

        self.left_panel = self._build_canvas_panel()
        self.right_panel = self._build_sidebar()

        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(18)

        root_layout.addWidget(self.left_panel, 1)
        root_layout.addWidget(self.right_panel)

        self.setCentralWidget(root)
        self._apply_styles()
        self.update_selection_panel()
        self.update_startup_buttons()

    def _build_canvas_panel(self):
        panel = QFrame()
        panel.setObjectName("CanvasPanel")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        title = QLabel("Display Layout")
        title.setObjectName("PageTitle")

        subtitle = QLabel("Drag displays, save/load profiles, then apply the layout.")
        subtitle.setObjectName("SubTitle")

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.canvas, 1)
        layout.addWidget(self.status_label)

        return panel

    def _build_sidebar(self):
        panel = QFrame()
        panel.setObjectName("SidePanel")
        panel.setFixedWidth(360)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        layout.addWidget(self.selection_title)
        layout.addWidget(self.selection_details)

        profiles_section = QFrame()
        profiles_section.setObjectName("InnerSection")
        profiles_layout = QVBoxLayout(profiles_section)
        profiles_layout.setContentsMargins(14, 14, 14, 14)
        profiles_layout.setSpacing(10)

        profiles_title = QLabel("Profiles")
        profiles_title.setObjectName("SectionTitle")
        profiles_layout.addWidget(profiles_title)
        profiles_layout.addWidget(self.save_button)
        profiles_layout.addWidget(self.load_button)
        profiles_layout.addWidget(self.load_apply_button)

        display_section = QFrame()
        display_section.setObjectName("InnerSection")
        display_layout = QVBoxLayout(display_section)
        display_layout.setContentsMargins(14, 14, 14, 14)
        display_layout.setSpacing(10)

        display_title = QLabel("Display Controls")
        display_title.setObjectName("SectionTitle")
        display_layout.addWidget(display_title)
        display_layout.addWidget(self.refresh_button)
        display_layout.addWidget(self.primary_button)
        display_layout.addWidget(self.apply_button)

        startup_section = QFrame()
        startup_section.setObjectName("InnerSection")
        startup_layout = QVBoxLayout(startup_section)
        startup_layout.setContentsMargins(14, 14, 14, 14)
        startup_layout.setSpacing(10)

        startup_title = QLabel("Startup Agent")
        startup_title.setObjectName("SectionTitle")
        startup_layout.addWidget(startup_title)
        startup_layout.addWidget(self.enable_startup_button)
        startup_layout.addWidget(self.disable_startup_button)

        layout.addWidget(profiles_section)
        layout.addWidget(display_section)
        layout.addWidget(startup_section)
        layout.addStretch(1)

        return panel

    def _apply_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background: #F1F5F9;
            }

            #CanvasPanel, #SidePanel {
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 18px;
            }

            #InnerSection {
                background: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 14px;
            }

            #PageTitle {
                color: #0F172A;
                font-size: 24px;
                font-weight: 700;
            }

            #SubTitle {
                color: #64748B;
                font-size: 13px;
                margin-bottom: 4px;
            }

            #SectionTitle {
                color: #0F172A;
                font-size: 16px;
                font-weight: 700;
            }

            #SelectionDetails {
                color: #475569;
                font-size: 13px;
                background: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
                padding: 12px;
            }

            #StatusLabel {
                color: #475569;
                font-size: 12px;
                background: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
                padding: 10px 12px;
            }

            QPushButton {
                min-height: 42px;
                border-radius: 12px;
                border: 1px solid #CBD5E1;
                background: #FFFFFF;
                color: #0F172A;
                font-size: 13px;
                font-weight: 600;
                padding: 0 14px;
            }

            QPushButton:hover {
                border: 1px solid #94A3B8;
            }

            QPushButton:pressed {
                background: #E2E8F0;
            }

            #PrimaryButton {
                background: #2563EB;
                color: white;
                border: 1px solid #2563EB;
            }

            #PrimaryButton:hover {
                background: #1D4ED8;
                border: 1px solid #1D4ED8;
            }

            #AccentButton {
                background: #EEF2FF;
                color: #3730A3;
                border: 1px solid #C7D2FE;
            }

            #AccentButton:hover {
                background: #E0E7FF;
                border: 1px solid #A5B4FC;
            }

            #SuccessButton {
                background: #ECFDF5;
                color: #166534;
                border: 1px solid #BBF7D0;
            }

            #SuccessButton:hover {
                background: #DCFCE7;
                border: 1px solid #86EFAC;
            }

            #WarningButton {
                background: #FFF7ED;
                color: #9A3412;
                border: 1px solid #FED7AA;
            }

            #WarningButton:hover {
                background: #FFEDD5;
                border: 1px solid #FDBA74;
            }

            #DangerButton {
                background: #FEF2F2;
                color: #991B1B;
                border: 1px solid #FECACA;
            }

            #DangerButton:hover {
                background: #FEE2E2;
                border: 1px solid #FCA5A5;
            }

            #NeutralButton {
                background: #FFFFFF;
                color: #0F172A;
                border: 1px solid #CBD5E1;
            }

            #NeutralButton:hover {
                background: #F8FAFC;
                border: 1px solid #94A3B8;
            }
        """)

    def update_startup_buttons(self):
        enabled = is_startup_agent_enabled()
        self.enable_startup_button.setEnabled(not enabled)
        self.disable_startup_button.setEnabled(enabled)

    def update_selection_panel(self):
        selected = self.canvas.get_selected_monitor()

        if not selected:
            self.selection_details.setText("No monitor selected")
            self.primary_button.setEnabled(False)
            return

        self.primary_button.setEnabled(not selected.get("primary", False))

        primary_text = "Yes" if selected.get("primary", False) else "No"
        clean_name = selected["name"].replace("\\\\.\\", "")

        details = (
            f'Name: {clean_name}\n'
            f'Friendly name: {selected.get("friendly_name", "Unknown")}\n'
            f'Resolution: {selected["width"]} × {selected["height"]}\n'
            f'Coordinates: ({selected["x"]}, {selected["y"]})\n'
            f'Primary: {primary_text}'
        )
        self.selection_details.setText(details)

    def on_refresh_clicked(self):
        self.canvas.refresh_monitors()
        self.update_selection_panel()
        self.status_label.setText("Layout refreshed from Windows.")

    def on_save_profile_clicked(self):
        try:
            save_profile(self.canvas.monitors, DEFAULT_PROFILE_PATH)
            self.status_label.setText(f"Profile saved to {DEFAULT_PROFILE_PATH}")
        except Exception as e:
            self.status_label.setText(f"Save failed: {e}")
            QMessageBox.critical(self, "DisplayMapper", f"Save failed:\n{e}")

    def on_load_profile_clicked(self):
        try:
            profile_data = load_profile(DEFAULT_PROFILE_PATH)
            updated_monitors = apply_profile_to_monitors(self.canvas.monitors, profile_data)
            self.canvas.set_monitors(updated_monitors)
            self.update_selection_panel()
            self.status_label.setText(f"Profile loaded from {DEFAULT_PROFILE_PATH}")
        except Exception as e:
            self.status_label.setText(f"Load failed: {e}")
            QMessageBox.critical(self, "DisplayMapper", f"Load failed:\n{e}")

    def on_load_apply_profile_clicked(self):
        try:
            profile_data = load_profile(DEFAULT_PROFILE_PATH)
            updated_monitors = apply_profile_to_monitors(self.canvas.monitors, profile_data)
            self.canvas.set_monitors(updated_monitors)
            apply_layout(updated_monitors)
            self.canvas.refresh_monitors()
            self.update_selection_panel()
            self.status_label.setText("Profile loaded and applied.")
        except Exception as e:
            self.status_label.setText(f"Load + Apply failed: {e}")
            QMessageBox.critical(self, "DisplayMapper", f"Load + Apply failed:\n{e}")

    def on_set_primary_clicked(self):
        selected = self.canvas.get_selected_monitor()
        if not selected:
            self.status_label.setText("Select a monitor first.")
            return

        self.canvas.set_selected_as_primary()
        self.update_selection_panel()
        self.status_label.setText("Primary monitor updated in editor. Click Apply Layout to commit.")

    def on_enable_startup_clicked(self):
        try:
            enable_startup_agent()
            self.update_startup_buttons()
            self.status_label.setText("Startup agent enabled.")
        except Exception as e:
            self.status_label.setText(f"Enable startup failed: {e}")
            QMessageBox.critical(self, "DisplayMapper", f"Enable startup failed:\n{e}")

    def on_disable_startup_clicked(self):
        try:
            disable_startup_agent()
            self.update_startup_buttons()
            self.status_label.setText("Startup agent disabled.")
        except Exception as e:
            self.status_label.setText(f"Disable startup failed: {e}")
            QMessageBox.critical(self, "DisplayMapper", f"Disable startup failed:\n{e}")

    def on_apply_clicked(self):
        try:
            apply_layout(self.canvas.monitors)
            self.canvas.refresh_monitors()
            self.update_selection_panel()
            self.status_label.setText("Layout applied successfully.")
        except Exception as e:
            self.status_label.setText(f"Apply failed: {e}")
            QMessageBox.critical(self, "DisplayMapper", f"Apply failed:\n{e}")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("DisplayMapper")
    app.setWindowIcon(QIcon(resource_path("DisplayMapper.ico")))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()