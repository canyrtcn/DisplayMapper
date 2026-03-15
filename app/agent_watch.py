import threading
import time

import win32con
import win32gui
import win32ts

from app.agent_once import run_agent_once

TRIGGER_COOLDOWN_SECONDS = 8.0


class AgentWatch:
    def __init__(self):
        self._last_trigger_time = 0.0
        self._class_name = "DisplayMapperWakeWatcher"
        self._hwnd = None

    def _can_trigger(self):
        now = time.time()
        if now - self._last_trigger_time < TRIGGER_COOLDOWN_SECONDS:
            return False
        self._last_trigger_time = now
        return True

    def _start_retry_worker(self):
        if not self._can_trigger():
            return
        threading.Thread(target=run_agent_once, daemon=True).start()

    def _wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == win32con.WM_POWERBROADCAST:
            if wparam in (
                getattr(win32con, "PBT_APMRESUMEAUTOMATIC", -1),
                getattr(win32con, "PBT_APMRESUMESUSPEND", -1),
            ):
                self._start_retry_worker()
            return 1

        if msg == getattr(win32con, "WM_WTSSESSION_CHANGE", 0x02B1):
            if wparam == getattr(win32ts, "WTS_SESSION_UNLOCK", -1):
                self._start_retry_worker()
            return 0

        if msg == win32con.WM_CLOSE:
            win32gui.DestroyWindow(hwnd)
            return 0

        if msg == win32con.WM_DESTROY:
            try:
                win32ts.WTSUnRegisterSessionNotification(hwnd)
            except Exception:
                pass
            win32gui.PostQuitMessage(0)
            return 0

        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def start(self):
        wc = win32gui.WNDCLASS()
        wc.lpfnWndProc = self._wnd_proc
        wc.lpszClassName = self._class_name
        wc.hInstance = win32gui.GetModuleHandle(None)

        try:
            class_atom = win32gui.RegisterClass(wc)
        except win32gui.error:
            class_atom = self._class_name

        self._hwnd = win32gui.CreateWindow(
            class_atom,
            self._class_name,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            wc.hInstance,
            None,
        )

        win32ts.WTSRegisterSessionNotification(
            self._hwnd,
            win32ts.NOTIFY_FOR_THIS_SESSION,
        )

        threading.Thread(target=run_agent_once, daemon=True).start()

        win32gui.PumpMessages()


def run_agent_watch():
    AgentWatch().start()