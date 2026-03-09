from app.core.apply_engine import apply_layout
from app.core.discovery import get_monitors
from app.core.profiles import (
    DEFAULT_PROFILE_PATH,
    apply_profile_to_monitors,
    load_profile,
    profile_matches_current,
)


def run_agent_once():
    try:
        profile_data = load_profile(DEFAULT_PROFILE_PATH)
    except FileNotFoundError:
        print("AgentOnce: no saved profile found.")
        return
    except (OSError, ValueError) as e:
        print("AgentOnce: profile load failed:", e)
        return

    try:
        current = get_monitors()

        if profile_matches_current(current, profile_data):
            print("AgentOnce: layout already correct.")
            return

        updated = apply_profile_to_monitors(current, profile_data)

        print("AgentOnce: applying saved layout...")
        apply_layout(updated)

    except (OSError, RuntimeError, ValueError) as e:
        print("AgentOnce: apply failed:", e)