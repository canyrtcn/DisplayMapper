import ctypes
import time

from app.core.apply_engine import apply_layout
from app.core.discovery import get_monitors
from app.core.profiles import (
    DEFAULT_PROFILE_PATH,
    apply_profile_to_monitors,
    load_profile,
    profile_matches_current,
)

user32 = ctypes.windll.user32

POLL_INTERVAL_SECONDS = 2.0
POST_READY_DELAY_SECONDS = 1.0


def _is_shell_ready():
    try:
        shell_hwnd = user32.GetShellWindow()
        tray_hwnd = user32.FindWindowW("Shell_TrayWnd", None)
        return bool(shell_hwnd) and bool(tray_hwnd)
    except Exception:
        return False


def _load_profile_safe():
    try:
        return load_profile(DEFAULT_PROFILE_PATH)
    except Exception:
        return None


def run_agent_once():
    print("AgentOnce: waiting for shell...")

    while not _is_shell_ready():
        time.sleep(1)

    time.sleep(POST_READY_DELAY_SECONDS)

    profile_data = _load_profile_safe()
    if profile_data is None:
        return

    while True:
        try:
            current = get_monitors()
        except Exception:
            time.sleep(POLL_INTERVAL_SECONDS)
            continue

        try:
            if profile_matches_current(current, profile_data):
                print("AgentOnce: layout correct. exiting.")
                return

            updated = apply_profile_to_monitors(current, profile_data)

            print("AgentOnce: applying layout...")
            apply_layout(updated)

        except Exception:
            pass

        time.sleep(POLL_INTERVAL_SECONDS)