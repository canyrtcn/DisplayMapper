import ctypes
from ctypes import wintypes


ENUM_CURRENT_SETTINGS = -1

DM_POSITION         = 0x00000020

CDS_UPDATEREGISTRY  = 0x00000001
CDS_NORESET         = 0x10000000
CDS_SET_PRIMARY     = 0x00000010

DISP_CHANGE_SUCCESSFUL = 0
DISP_CHANGE_RESTART    = 1

CCHDEVICENAME = 32
CCHFORMNAME   = 32


class POINTL(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class _DUMMYSTRUCTNAME(ctypes.Structure):
    _fields_ = [
        ("dmPosition",           POINTL),
        ("dmDisplayOrientation", wintypes.DWORD),
        ("dmDisplayFixedOutput", wintypes.DWORD),
    ]


class _DUMMYUNIONNAME(ctypes.Union):
    _fields_ = [
        ("dmDisplayFlags", wintypes.DWORD),
        ("dmNup",          wintypes.DWORD),
    ]


class DEVMODEW(ctypes.Structure):
    _anonymous_ = ("u1", "u2")
    _fields_ = [
        ("dmDeviceName",       wintypes.WCHAR * CCHDEVICENAME),
        ("dmSpecVersion",      wintypes.WORD),
        ("dmDriverVersion",    wintypes.WORD),
        ("dmSize",             wintypes.WORD),
        ("dmDriverExtra",      wintypes.WORD),
        ("dmFields",           wintypes.DWORD),
        ("u1",                 _DUMMYSTRUCTNAME),
        ("dmColor",            wintypes.SHORT),
        ("dmDuplex",           wintypes.SHORT),
        ("dmYResolution",      wintypes.SHORT),
        ("dmTTOption",         wintypes.SHORT),
        ("dmCollate",          wintypes.SHORT),
        ("dmFormName",         wintypes.WCHAR * CCHFORMNAME),
        ("dmLogPixels",        wintypes.WORD),
        ("dmBitsPerPel",       wintypes.DWORD),
        ("dmPelsWidth",        wintypes.DWORD),
        ("dmPelsHeight",       wintypes.DWORD),
        ("u2",                 _DUMMYUNIONNAME),
        ("dmDisplayFrequency", wintypes.DWORD),
        ("dmICMMethod",        wintypes.DWORD),
        ("dmICMIntent",        wintypes.DWORD),
        ("dmMediaType",        wintypes.DWORD),
        ("dmDitherType",       wintypes.DWORD),
        ("dmReserved1",        wintypes.DWORD),
        ("dmReserved2",        wintypes.DWORD),
        ("dmPanningWidth",     wintypes.DWORD),
        ("dmPanningHeight",    wintypes.DWORD),
    ]


user32 = ctypes.WinDLL("user32", use_last_error=True)

_EnumDisplaySettingsW = user32.EnumDisplaySettingsW
_EnumDisplaySettingsW.argtypes = [
    wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(DEVMODEW)
]
_EnumDisplaySettingsW.restype = wintypes.BOOL

_ChangeDisplaySettingsExW = user32.ChangeDisplaySettingsExW
_ChangeDisplaySettingsExW.argtypes = [
    wintypes.LPCWSTR, ctypes.POINTER(DEVMODEW),
    wintypes.HWND, wintypes.DWORD, wintypes.LPVOID,
]
_ChangeDisplaySettingsExW.restype = wintypes.LONG


def _normalize_device_name(name: str) -> str:
    if name.startswith("\\\\.\\"):
        return name
    upper = name.upper()
    if upper.startswith("DISPLAY"):
        return f"\\\\.\\{upper}"
    return name


def _prepare_monitors(monitors):

    if not monitors:
        raise ValueError("No monitors to apply.")
    primaries = [m for m in monitors if m.get("primary")]
    if len(primaries) != 1:
        raise ValueError("Exactly one primary monitor is required.")
    primary = primaries[0]
    ox, oy = int(primary["x"]), int(primary["y"])
    return [
        {
            "name":    _normalize_device_name(m["name"]),
            "x":       int(m["x"]) - ox,
            "y":       int(m["y"]) - oy,
            "width":   int(m.get("width",  0)),
            "height":  int(m.get("height", 0)),
            "primary": bool(m.get("primary", False)),
        }
        for m in monitors
    ]


def _get_devmode(device_name: str) -> DEVMODEW:
    dm = DEVMODEW()
    dm.dmSize = ctypes.sizeof(DEVMODEW)
    if not _EnumDisplaySettingsW(device_name, ENUM_CURRENT_SETTINGS,
                                  ctypes.byref(dm)):
        raise RuntimeError(f"EnumDisplaySettingsW failed for {device_name}")
    return dm


def _ok(code: int) -> bool:
    return code in (DISP_CHANGE_SUCCESSFUL, DISP_CHANGE_RESTART)


def _cds(device_name: str, x: int, y: int,
         is_primary: bool, noreset: bool) -> int:

    dm = _get_devmode(device_name)
    dm.dmPosition.x = x
    dm.dmPosition.y = y
    dm.dmFields = DM_POSITION          # position only — driver keeps the rest

    flags = CDS_UPDATEREGISTRY
    if noreset:
        flags |= CDS_NORESET
    if is_primary:
        flags |= CDS_SET_PRIMARY

    return _ChangeDisplaySettingsExW(
        device_name, ctypes.byref(dm), None, flags, None)


def _commit() -> int:
    return _ChangeDisplaySettingsExW(None, None, None, 0, None)


def apply_layout(monitors):

    prepared    = _prepare_monitors(monitors)
    new_primary = next(m for m in prepared if m["primary"])
    secondaries = [m for m in prepared if not m["primary"]]

    errors = []

    # ------------------------------------------------------------------ #
    # Pass 1 – batched (CDS_NORESET)                                      #
    # Step A: promote new primary to (0,0) — staged                      #
    # Step B: position every secondary    — staged                        #
    # Step C: commit                                                      #
    # ------------------------------------------------------------------ #
    ok, errs = True, []

    r = _cds(new_primary["name"], 0, 0, True, noreset=True)
    if not _ok(r):
        ok = False
        errs.append(f"pass1 promote {new_primary['name']}: code {r}")

    for m in secondaries:
        r = _cds(m["name"], m["x"], m["y"], False, noreset=True)
        if not _ok(r):
            ok = False
            errs.append(f"pass1 position {m['name']}: code {r}")

    if ok:
        r = _commit()
        if _ok(r):
            # Correct primary's position if it wasn't meant to stay at (0,0)
            if new_primary["x"] != 0 or new_primary["y"] != 0:
                _cds(new_primary["name"],
                     new_primary["x"], new_primary["y"],
                     True, noreset=False)
            return
        errs.append(f"pass1 commit: code {r}")

    errors.extend(errs)

    # ------------------------------------------------------------------ #
    # Pass 2 – immediate (no CDS_NORESET)                                 #
    # Same order, each call self-commits.                                 #
    # ------------------------------------------------------------------ #
    ok, errs = True, []

    r = _cds(new_primary["name"], 0, 0, True, noreset=False)
    if not _ok(r):
        ok = False
        errs.append(f"pass2 promote {new_primary['name']}: code {r}")

    for m in secondaries:
        r = _cds(m["name"], m["x"], m["y"], False, noreset=False)
        if not _ok(r):
            ok = False
            errs.append(f"pass2 position {m['name']}: code {r}")

    if ok:
        if new_primary["x"] != 0 or new_primary["y"] != 0:
            _cds(new_primary["name"],
                 new_primary["x"], new_primary["y"],
                 True, noreset=False)
        return

    errors.extend(errs)

    raise RuntimeError(
        "apply_layout: all attempts failed.\n" + "\n".join(errors)
    )
