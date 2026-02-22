"""
Mouse Trail Server - Captures TRUE hardware mouse deltas via Windows Raw Input API.
Streams deltas over WebSocket to the overlay. Works in all games — raw input is
independent of cursor position, so cursor-centering by FPS games is irrelevant.

Usage:
  py mouse_server.py
  py mouse_server.py --port 8765
"""

import asyncio
import json
import argparse
import threading
import time
import struct
import ctypes
import ctypes.wintypes as wt
from ctypes import Structure, WINFUNCTYPE, byref, sizeof
from collections import deque

import websockets

# --- Win32 setup ---
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

user32.DefWindowProcW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
user32.DefWindowProcW.restype = ctypes.c_long
user32.GetRawInputData.argtypes = [
    ctypes.c_void_p, wt.UINT, ctypes.c_void_p, ctypes.POINTER(wt.UINT), wt.UINT
]
user32.GetRawInputData.restype = wt.UINT

WM_INPUT = 0x00FF
RIDEV_INPUTSINK = 0x00000100
RID_INPUT = 0x10000003

WNDPROC = WINFUNCTYPE(ctypes.c_long, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)


class WNDCLASSEXW(Structure):
    _fields_ = [
        ("cbSize", wt.UINT), ("style", wt.UINT), ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
        ("hInstance", wt.HINSTANCE), ("hIcon", wt.HICON), ("hCursor", wt.HANDLE),
        ("hbrBackground", wt.HBRUSH), ("lpszMenuName", wt.LPCWSTR),
        ("lpszClassName", wt.LPCWSTR), ("hIconSm", wt.HICON),
    ]


class RAWINPUTHEADER(Structure):
    _fields_ = [
        ("dwType", wt.DWORD), ("dwSize", wt.DWORD),
        ("hDevice", wt.HANDLE), ("wParam", wt.WPARAM),
    ]


class RAWINPUTDEVICE(Structure):
    _fields_ = [
        ("usUsagePage", wt.USHORT), ("usUsage", wt.USHORT),
        ("dwFlags", wt.DWORD), ("hwndTarget", wt.HWND),
    ]


# --- Shared state ---
delta_buffer = deque(maxlen=500)
lock = threading.Lock()
clients = set()

# RAWINPUTHEADER size (24 on x64)
HDR_SZ = sizeof(RAWINPUTHEADER)


def _noop_wndproc(hwnd, msg, wparam, lparam):
    return user32.DefWindowProcW(hwnd, msg, wparam, wt.LPARAM(lparam))


_wndproc_ref = WNDPROC(_noop_wndproc)


def raw_input_thread():
    """Create a hidden window, register for raw mouse input, poll messages."""
    hInst = kernel32.GetModuleHandleW(None)
    cls_name = "MouseTrailRawInput"

    wc = WNDCLASSEXW()
    wc.cbSize = sizeof(WNDCLASSEXW)
    wc.lpfnWndProc = _wndproc_ref
    wc.hInstance = hInst
    wc.lpszClassName = cls_name

    if not user32.RegisterClassExW(byref(wc)):
        print(f"  RegisterClassEx failed: {ctypes.GetLastError()}")
        return

    # WS_OVERLAPPEDWINDOW is required for raw input delivery
    hwnd = user32.CreateWindowExW(
        0, cls_name, "MouseTrail", 0x00CF0000,
        0, 0, 1, 1,
        None, None, hInst, None,
    )
    if not hwnd:
        print(f"  CreateWindowEx failed: {ctypes.GetLastError()}")
        return

    user32.ShowWindow(hwnd, 0)  # SW_HIDE

    rid = RAWINPUTDEVICE()
    rid.usUsagePage = 0x01  # HID_USAGE_PAGE_GENERIC
    rid.usUsage = 0x02      # HID_USAGE_GENERIC_MOUSE
    rid.dwFlags = RIDEV_INPUTSINK
    rid.hwndTarget = hwnd

    if not user32.RegisterRawInputDevices(byref(rid), 1, sizeof(RAWINPUTDEVICE)):
        print(f"  RegisterRawInputDevices failed: {ctypes.GetLastError()}")
        return

    print(f"  Raw input active (hwnd={hwnd}, hdr={HDR_SZ}B)")

    msg = wt.MSG()
    while True:
        # PeekMessage with hwnd=None retrieves ALL thread messages including WM_INPUT
        while user32.PeekMessageW(byref(msg), None, 0, 0, 1):  # PM_REMOVE=1
            if msg.message == WM_INPUT:
                _process_raw_input(msg.lParam)
            user32.TranslateMessage(byref(msg))
            user32.DispatchMessageW(byref(msg))
        time.sleep(0.001)  # ~1000Hz poll


def _process_raw_input(lParam):
    """Extract mouse dx/dy from a WM_INPUT message."""
    hRI = ctypes.c_void_p(lParam)
    size = wt.UINT(0)
    user32.GetRawInputData(hRI, RID_INPUT, None, byref(size), HDR_SZ)
    if size.value == 0:
        return

    buf = ctypes.create_string_buffer(size.value)
    ret = user32.GetRawInputData(hRI, RID_INPUT, buf, byref(size), HDR_SZ)
    if ret == 0 or ret == 0xFFFFFFFF:
        return

    raw = buf.raw
    # Check dwType == RIM_TYPEMOUSE (0)
    if struct.unpack_from('I', raw, 0)[0] != 0:
        return

    m = HDR_SZ
    # usFlags at offset 0 of RAWMOUSE — 0 means MOUSE_MOVE_RELATIVE
    if struct.unpack_from('H', raw, m)[0] != 0:
        return

    dx = struct.unpack_from('l', raw, m + 12)[0]
    dy = struct.unpack_from('l', raw, m + 16)[0]
    if dx != 0 or dy != 0:
        with lock:
            delta_buffer.append((dx, dy))


async def broadcast_deltas():
    """Send accumulated deltas to all connected clients at ~60fps."""
    global clients
    while True:
        await asyncio.sleep(1 / 60)
        with lock:
            if not delta_buffer or not clients:
                continue
            batch = list(delta_buffer)
            delta_buffer.clear()

        msg = json.dumps({"deltas": [[d[0], d[1]] for d in batch]})
        dead = set()
        # snapshot the set — handlers may modify `clients` during await
        for ws in list(clients):
            try:
                await ws.send(msg)
            except Exception:
                dead.add(ws)
        clients -= dead


async def handler(ws):
    clients.add(ws)
    print(f"Client connected ({len(clients)} total)")
    try:
        async for msg in ws:
            pass
    except Exception:
        pass
    finally:
        clients.discard(ws)
        print(f"Client disconnected ({len(clients)} total)")


async def main(port):
    print(f"Mouse trail server on ws://localhost:{port}")
    print("Using Windows Raw Input API (hardware mouse deltas)")

    t = threading.Thread(target=raw_input_thread, daemon=True)
    t.start()
    time.sleep(0.3)

    print("Add overlay.html as OBS Browser Source")
    print("Press Ctrl+C to stop\n")

    async with websockets.serve(handler, "localhost", port, ping_interval=None, ping_timeout=None):
        await broadcast_deltas()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mouse Trail WebSocket Server")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    try:
        asyncio.run(main(args.port))
    except KeyboardInterrupt:
        print("\nStopped.")
