# Mouse Trail for OBS

Draws a real-time mouse movement trail as an OBS overlay — like dragging a crayon
under your mouse on the mousepad. Uses the **Windows Raw Input API** to read
hardware mouse deltas directly, so it works in all games regardless of cursor
locking, centering, or sensitivity settings.

## Files

| File | What it does |
|------|-------------|
| `launcher.pyw` | GUI launcher — double-click to open. Configure everything, start the server, copy the OBS path. |
| `mouse_server.py` | Python WebSocket server. Captures raw hardware mouse deltas via Win32 Raw Input API and streams them to the overlay. |
| `overlay.html` | HTML/JS canvas overlay — added to OBS as a Browser Source. |

## Quick Start

1. **Double-click `launcher.pyw`**
2. Adjust trail color, width, glow, fade, etc.
3. Click **Start Server**
4. Click the green OBS URL bar to copy it
5. In OBS: Sources > + > Browser > paste the URL
6. Set width/height to your canvas size (e.g. 1920x1080)
7. Done — works in-game immediately, no game mode toggle needed

## Manual Start (no GUI)

```bash
py mouse_server.py
py mouse_server.py --port 9000
```

Then add this as an OBS Browser Source:
```
C:\Users\User\Documents\Videos\Stream assets\mouse-trail\overlay.html
```

## How It Works

```
Mouse hardware ──► Win32 Raw Input API ──► mouse_server.py ──► WebSocket ──► overlay.html canvas
```

The server creates a hidden window registered for `RIDEV_INPUTSINK` raw mouse
input. The Raw Input API delivers **hardware-level deltas** (dx, dy) on every
mouse movement — these are the actual distance the sensor reported, completely
independent of:

- Cursor position on screen
- Games calling `SetCursorPos()` to recenter the mouse
- Mouse acceleration / sensitivity settings in Windows
- Which monitor or window has focus

No game mode, no center-point detection, no hacks. Just real mouse movement data.

## Overlay Controls

Press **F7** on the overlay page (or in OBS interact mode) to toggle the control panel.

| Control | What it does |
|---------|-------------|
| Width | Line thickness (1-20 px) |
| Opacity | Trail opacity |
| Fade | Seconds before trail fades out (0 = permanent) |
| Color | Trail color |
| Glow | Neon glow intensity |
| Scale | Delta sensitivity multiplier |
| Camera | How tightly the viewport follows the pen (1 = slow drift, 100 = locked on) |
| Preset | Quick style switch — **Neon** (thick, glowing) or **Pen** (thin, no glow, dimmed trail) |
| Dim Trail | Older segments fade to 5% brightness, newest at 100% (recency-based dimming) |
| Instafade | Overrides fade to ~0.3s for a short comet-tail effect. Combines well with Dim Trail. |
| Cursor Only | Hides the trail, shows only a dot at the current pen position |
| Endpoints | One line per server batch instead of every micro-delta — simplified "connect the dots" path |
| Arrow | Draws a direction arrowhead at the pen position showing current movement direction |
| Clear | Wipe all segments |
| Disable/Enable | Toggle drawing |
| Export URL | Generate URL with all settings as query params for OBS |

## Requirements

- Python 3.10+
- `pip install websockets`
- Windows 10/11 (uses Win32 Raw Input API)
