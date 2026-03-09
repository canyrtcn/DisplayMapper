import win32api
import win32con


DISPLAY_DEVICE_ATTACHED_TO_DESKTOP = getattr(
    win32con, "DISPLAY_DEVICE_ATTACHED_TO_DESKTOP", 0x00000001
)
DISPLAY_DEVICE_PRIMARY_DEVICE = getattr(
    win32con, "DISPLAY_DEVICE_PRIMARY_DEVICE", 0x00000004
)


def get_monitors():
    monitors = []

    i = 0
    while True:
        try:
            device = win32api.EnumDisplayDevices(None, i, 0)
        except win32api.error:
            break

        if device.StateFlags & DISPLAY_DEVICE_ATTACHED_TO_DESKTOP:
            settings = win32api.EnumDisplaySettings(
                device.DeviceName,
                win32con.ENUM_CURRENT_SETTINGS
            )

            monitors.append({
                "name": device.DeviceName,
                "friendly_name": device.DeviceString,
                "width": int(settings.PelsWidth),
                "height": int(settings.PelsHeight),
                "x": int(settings.Position_x),
                "y": int(settings.Position_y),
                "primary": bool(device.StateFlags & DISPLAY_DEVICE_PRIMARY_DEVICE),
            })

        i += 1

    return monitors