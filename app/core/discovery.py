import re

import win32api
import win32con
import win32com.client


DISPLAY_DEVICE_ATTACHED_TO_DESKTOP = 0x00000001
DISPLAY_DEVICE_PRIMARY_DEVICE = 0x00000004

GPU_KEYWORDS = (
    "NVIDIA",
    "GEFORCE",
    "AMD",
    "RADEON",
    "INTEL",
    "GRAPHICS",
)


def _decode_wmi_string(char_array):
    return "".join(chr(x) for x in char_array if x != 0).strip()


def _normalize_instance_name(value):
    return str(value).upper().replace("_0", "")


def _extract_monitor_hardware_id(device_id):
    if not device_id:
        return None

    match = re.search(r"MONITOR\\([^\\]+)", str(device_id), re.IGNORECASE)
    if match:
        return match.group(1).upper()

    return None


def _looks_like_gpu_name(text):
    upper = str(text).upper()
    return any(keyword in upper for keyword in GPU_KEYWORDS)


def _load_wmi_monitor_names():
    names = {}

    try:
        locator = win32com.client.Dispatch("WbemScripting.SWbemLocator")
        service = locator.ConnectServer(".", "root\\wmi")
        rows = service.ExecQuery(
            "SELECT InstanceName, UserFriendlyName FROM WmiMonitorID"
        )

        for row in rows:
            instance_name = _normalize_instance_name(row.InstanceName)
            friendly_name = _decode_wmi_string(row.UserFriendlyName)

            if friendly_name:
                names[instance_name] = friendly_name
    except Exception:
        pass

    return names


def _find_wmi_name_for_device_id(device_id, wmi_names):
    if not device_id:
        return None

    device_id_upper = str(device_id).upper()
    hardware_id = _extract_monitor_hardware_id(device_id)

    for instance_name, friendly_name in wmi_names.items():
        if hardware_id and hardware_id in instance_name:
            return friendly_name

        if device_id_upper in instance_name:
            return friendly_name

    return None


def get_monitors():
    monitors = []
    wmi_names = _load_wmi_monitor_names()

    i = 0
    while True:
        try:
            adapter = win32api.EnumDisplayDevices(None, i, 0)
        except win32api.error:
            break

        if adapter.StateFlags & DISPLAY_DEVICE_ATTACHED_TO_DESKTOP:
            settings = win32api.EnumDisplaySettings(
                adapter.DeviceName,
                win32con.ENUM_CURRENT_SETTINGS
            )

            friendly_name = None

            j = 0
            while True:
                try:
                    child = win32api.EnumDisplayDevices(adapter.DeviceName, j, 0)
                except win32api.error:
                    break

                child_id = str(getattr(child, "DeviceID", "") or "")
                child_name = str(getattr(child, "DeviceString", "") or "").strip()

                wmi_name = _find_wmi_name_for_device_id(child_id, wmi_names)
                if wmi_name:
                    friendly_name = wmi_name
                    break

                if child_name and not _looks_like_gpu_name(child_name):
                    friendly_name = child_name

                j += 1

            if not friendly_name:
                friendly_name = adapter.DeviceName.replace("\\\\.\\", "")

            monitors.append({
                "name": adapter.DeviceName,
                "friendly_name": friendly_name,
                "width": int(settings.PelsWidth),
                "height": int(settings.PelsHeight),
                "x": int(settings.Position_x),
                "y": int(settings.Position_y),
                "primary": bool(adapter.StateFlags & DISPLAY_DEVICE_PRIMARY_DEVICE),
            })

        i += 1

    return monitors