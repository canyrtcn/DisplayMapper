import json
import os
from typing import Any, Dict, List


APP_DIR = os.path.join(os.getenv("LOCALAPPDATA", ""), "DisplayMapper")
PROFILES_DIR = os.path.join(APP_DIR, "profiles")
DEFAULT_PROFILE_PATH = os.path.join(PROFILES_DIR, "default.json")


def ensure_profile_dirs():
    os.makedirs(PROFILES_DIR, exist_ok=True)


def _serialize_monitors(monitors: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "version": 1,
        "monitors": [
            {
                "name": m["name"],
                "x": int(m["x"]),
                "y": int(m["y"]),
                "width": int(m["width"]),
                "height": int(m["height"]),
                "primary": bool(m.get("primary", False)),
            }
            for m in monitors
        ]
    }


def save_profile(monitors: List[Dict[str, Any]], path: str = DEFAULT_PROFILE_PATH):
    ensure_profile_dirs()

    payload = _serialize_monitors(monitors)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def load_profile(path: str = DEFAULT_PROFILE_PATH) -> Dict[str, Any]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Profile not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def apply_profile_to_monitors(current_monitors: List[Dict[str, Any]], profile_data: Dict[str, Any]):
    saved_monitors = profile_data.get("monitors", [])
    saved_by_name = {m["name"]: m for m in saved_monitors}

    updated = []
    for current in current_monitors:
        copy_monitor = dict(current)

        if current["name"] in saved_by_name:
            saved = saved_by_name[current["name"]]
            copy_monitor["x"] = int(saved["x"])
            copy_monitor["y"] = int(saved["y"])
            copy_monitor["primary"] = bool(saved.get("primary", False))

        updated.append(copy_monitor)

    primary_names = [m["name"] for m in updated if m.get("primary", False)]
    if primary_names:
        chosen = primary_names[0]
        for m in updated:
            m["primary"] = (m["name"] == chosen)

    return updated


def profile_matches_current(current_monitors: List[Dict[str, Any]], profile_data: Dict[str, Any]) -> bool:
    saved_monitors = profile_data.get("monitors", [])
    saved_by_name = {m["name"]: m for m in saved_monitors}
    current_by_name = {m["name"]: m for m in current_monitors}

    if set(saved_by_name.keys()) != set(current_by_name.keys()):
        return False

    for name, current in current_by_name.items():
        saved = saved_by_name[name]

        if int(current["x"]) != int(saved["x"]):
            return False
        if int(current["y"]) != int(saved["y"]):
            return False
        if bool(current.get("primary", False)) != bool(saved.get("primary", False)):
            return False

    return True