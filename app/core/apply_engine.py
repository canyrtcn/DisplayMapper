import win32api
import win32con
from typing import Any, cast


def apply_layout(monitors):
    for m in monitors:
        devmode = win32api.EnumDisplaySettings(
            m["name"],
            win32con.ENUM_CURRENT_SETTINGS
        )

        devmode.Position_x = int(m["x"])
        devmode.Position_y = int(m["y"])
        devmode.Fields |= win32con.DM_POSITION

        if m.get("primary", False):
            flags = (
                win32con.CDS_UPDATEREGISTRY
                | win32con.CDS_NORESET
                | win32con.CDS_SET_PRIMARY
            )
        else:
            flags = win32con.CDS_UPDATEREGISTRY | win32con.CDS_NORESET

        devmode_casted = cast(Any, devmode)

        result = win32api.ChangeDisplaySettingsEx(
            DeviceName=m["name"],
            DevMode=devmode_casted,  # type: ignore[arg-type]
            Flags=flags
        )

        print(f"{m['name']} -> result: {result}")

    final_result = win32api.ChangeDisplaySettingsEx()
    print(f"Final apply result: {final_result}")