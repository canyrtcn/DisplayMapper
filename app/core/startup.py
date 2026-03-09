import os
import sys
from pathlib import Path

from win32com.client import Dispatch


APP_SHORTCUT_NAME = "DisplayMapper Agent.lnk"


def get_startup_folder() -> str:
    return str(Path(os.getenv("APPDATA", "")) / r"Microsoft\Windows\Start Menu\Programs\Startup")


def get_startup_shortcut_path() -> str:
    return str(Path(get_startup_folder()) / APP_SHORTCUT_NAME)


def _build_command():
    """
    Development mode:
        pythonw.exe <project>/main.py --agent-once

    PyInstaller onedir/onefile mode:
        DisplayMapper.exe --agent-once
    """
    if getattr(sys, "frozen", False):
        target_path = sys.executable
        arguments = "--agent-once"
        working_directory = os.path.dirname(sys.executable)
        return target_path, arguments, working_directory

    pythonw_path = sys.executable.replace("python.exe", "pythonw.exe")
    if not os.path.exists(pythonw_path):
        pythonw_path = sys.executable

    script_path = os.path.abspath(sys.argv[0])
    target_path = pythonw_path
    arguments = f'"{script_path}" --agent-once'
    working_directory = os.path.dirname(script_path)
    return target_path, arguments, working_directory


def enable_startup_agent():
    os.makedirs(get_startup_folder(), exist_ok=True)

    shortcut_path = get_startup_shortcut_path()
    target_path, arguments, working_directory = _build_command()

    shell = Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(shortcut_path)
    shortcut.Targetpath = target_path
    shortcut.Arguments = arguments
    shortcut.WorkingDirectory = working_directory
    shortcut.IconLocation = target_path
    shortcut.save()


def disable_startup_agent():
    shortcut_path = get_startup_shortcut_path()
    if os.path.exists(shortcut_path):
        os.remove(shortcut_path)


def is_startup_agent_enabled() -> bool:
    return os.path.exists(get_startup_shortcut_path())