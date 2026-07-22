#!/usr/bin/env python3
"""
Fire TV MCP Server
==================
Lets Claude act as a remote control for an Amazon Fire TV Stick / Cube
over ADB (Wi-Fi). Works with Claude Desktop and Claude Code.

Requirements:
  - Python 3.10+
  - `pip install mcp`
  - ADB (Android platform-tools) installed on this computer
  - Fire TV with "ADB Debugging" enabled (Settings > My Fire TV > Developer Options)
  - Fire TV and this computer on the same network

Configuration (environment variables, all optional):
  FIRETV_IP   - IP address of the Fire TV (e.g. 192.168.1.42). If not set,
                use the firetv_connect tool once; the IP is remembered in
                ~/.firetv_mcp.json afterwards.
  FIRETV_ADB  - Full path to the adb executable, if it is not on PATH.
"""

import ipaddress
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    from mcp.server.fastmcp import FastMCP, Image
except ImportError:
    sys.stderr.write(
        "The 'mcp' package is not installed. Run:  pip install mcp\n"
    )
    sys.exit(1)

mcp = FastMCP("firetv")

STATE_FILE = Path.home() / ".firetv_mcp.json"
ADB_TIMEOUT = 20  # seconds

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def find_adb() -> str | None:
    """Locate the adb executable."""
    env_path = os.environ.get("FIRETV_ADB")
    if env_path and Path(env_path).exists():
        return env_path
    which = shutil.which("adb")
    if which:
        return which
    candidates = [
        # Windows
        Path(os.environ.get("LOCALAPPDATA", "")) / "Android/Sdk/platform-tools/adb.exe",
        Path("C:/platform-tools/adb.exe"),
        Path.home() / "platform-tools/adb.exe",
        # macOS / Linux
        Path("/opt/homebrew/bin/adb"),
        Path("/usr/local/bin/adb"),
        Path("/usr/bin/adb"),
        Path.home() / "platform-tools/adb",
    ]
    for c in candidates:
        if c and str(c) != "." and c.exists():
            return str(c)
    return None


def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {}


def save_state(state: dict) -> None:
    try:
        STATE_FILE.write_text(json.dumps(state))
    except Exception:
        pass


def saved_ip() -> str | None:
    return os.environ.get("FIRETV_IP") or load_state().get("ip")


def run_adb(args: list[str], binary: bool = False) -> tuple[bool, str | bytes]:
    """Run an adb command. Returns (ok, output)."""
    adb = find_adb()
    if not adb:
        return False, (
            "adb was not found on this computer. Install Android platform-tools "
            "(see the setup guide) or set the FIRETV_ADB environment variable "
            "to the full path of the adb executable."
        )
    try:
        result = subprocess.run(
            [adb] + args,
            capture_output=True,
            timeout=ADB_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return False, f"adb {' '.join(args)} timed out after {ADB_TIMEOUT}s."
    except OSError as e:
        return False, f"Failed to run adb: {e}"
    if binary:
        if result.returncode != 0:
            return False, result.stderr.decode(errors="replace")
        return True, result.stdout
    out = result.stdout.decode(errors="replace") + result.stderr.decode(errors="replace")
    return result.returncode == 0, out.strip()


def connected_device() -> str | None:
    """Return the serial of a connected device, or None."""
    ok, out = run_adb(["devices"])
    if not ok or isinstance(out, bytes):
        return None
    for line in out.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            return parts[0]
    return None


def ensure_connected() -> tuple[bool, str]:
    """Make sure a Fire TV is connected; auto-reconnect using the saved IP."""
    if connected_device():
        return True, "connected"
    ip = saved_ip()
    if not ip:
        return False, (
            "No Fire TV is connected and no IP address is saved. "
            "Ask the user for the Fire TV's IP address "
            "(on the TV: Settings > My Fire TV > About > Network) and call "
            "firetv_connect with it."
        )
    run_adb(["connect", f"{ip}:5555"])
    if connected_device():
        return True, "reconnected"
    return False, (
        f"Could not connect to the Fire TV at {ip}. Check that: the TV is on, "
        "ADB Debugging is enabled (Settings > My Fire TV > Developer Options), "
        "both devices are on the same Wi-Fi network, and any 'Allow USB "
        "debugging?' popup on the TV screen has been accepted. Then call "
        "firetv_connect again."
    )


# Named buttons -> Android keyevent codes
BUTTONS = {
    "up": 19, "down": 20, "left": 21, "right": 22,
    "select": 23, "ok": 23, "enter": 23, "center": 23,
    "home": 3, "back": 4, "menu": 82,
    "play_pause": 85, "play": 126, "pause": 127, "stop": 86,
    "rewind": 89, "fast_forward": 90, "next": 87, "previous": 88,
    "volume_up": 24, "volume_down": 25, "mute": 164,
    "channel_up": 166, "channel_down": 167,
    "sleep": 223, "wake": 224, "power": 26,
    "settings": 176, "search": 84, "info": 165,
    "guide": 172, "dvr": 173, "captions": 175,
}

# Friendly app names -> Fire TV package names (best-effort; use
# firetv_list_apps to discover what is actually installed).
APPS = {
    "netflix": "com.netflix.ninja",
    "prime video": "com.amazon.avod",
    "prime": "com.amazon.avod",
    "youtube": "com.amazon.firetv.youtube",
    "youtube tv": "com.amazon.firetv.youtube.tv",
    "disney+": "com.disney.disneyplus",
    "disney plus": "com.disney.disneyplus",
    "hulu": "com.hulu.plus",
    "max": "com.wbd.stream",
    "hbo max": "com.wbd.stream",
    "apple tv": "com.apple.atve.amazon.appletv",
    "spotify": "com.spotify.tv.android",
    "plex": "com.plexapp.android",
    "paramount+": "com.cbs.ott",
    "paramount plus": "com.cbs.ott",
    "peacock": "com.peacocktv.peacockandroid",
    "tubi": "com.tubitv",
    "pluto tv": "tv.pluto.android",
    "pluto": "tv.pluto.android",
    "espn": "com.espn.score_center",
    "sling": "com.sling",
    "twitch": "tv.twitch.android.app",
    "vlc": "org.videolan.vlc",
    "kodi": "org.xbmc.kodi",
    "amazon music": "com.amazon.bueller.music",
    "freevee": "com.amazon.imdb.tv.android.app",
}


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def firetv_connect(ip: str = "") -> str:
    """Connect to the Fire TV over the network.

    Args:
        ip: The Fire TV's IP address (e.g. '192.168.1.42'), found on the TV
            under Settings > My Fire TV > About > Network. Optional if an IP
            was saved previously or FIRETV_IP is set.
    """
    ip = ip.strip()
    if not ip:
        ip = saved_ip() or ""
    if not ip:
        return (
            "No IP address provided or saved. Ask the user to look it up on "
            "the TV under Settings > My Fire TV > About > Network."
        )
    ip = ip.replace("http://", "").split(":")[0]
    try:
        ipaddress.ip_address(ip)
    except ValueError:
        return f"'{ip}' is not a valid IP address."
    ok, out = run_adb(["connect", f"{ip}:5555"])
    device = connected_device()
    if device:
        state = load_state()
        state["ip"] = ip
        save_state(state)
        # Identify the device model for a friendlier message
        _, model = run_adb(["shell", "getprop", "ro.product.model"])
        return f"Connected to Fire TV at {ip} (model: {model}). IP saved for future sessions."
    return (
        f"adb said: {out}\n\nNot connected yet. If this is the first time, "
        "look at the TV screen - there may be an 'Allow USB debugging?' popup. "
        "Tell the user to select 'Always allow from this computer' and OK, "
        "then call firetv_connect again. Also verify ADB Debugging is ON "
        "(Settings > My Fire TV > Developer Options) and both devices share "
        "the same Wi-Fi."
    )


@mcp.tool()
def firetv_status() -> str:
    """Check whether a Fire TV is connected, and what app is on screen."""
    ok, msg = ensure_connected()
    if not ok:
        return msg
    _, model = run_adb(["shell", "getprop", "ro.product.model"])
    _, wake = run_adb(["shell", "dumpsys", "power"])
    awake = "unknown"
    if isinstance(wake, str):
        m = re.search(r"mWakefulness=(\w+)", wake)
        if m:
            awake = m.group(1)
    return (
        f"Fire TV connected ({msg}). Model: {model}. Power state: {awake}. "
        f"Foreground app: {_current_app() or 'unknown'}"
    )


def _current_app() -> str | None:
    ok, out = run_adb(["shell", "dumpsys", "window"])
    if ok and isinstance(out, str):
        m = re.search(r"mCurrentFocus=.*?\s([\w.]+)/[\w.$]+", out)
        if m:
            return m.group(1)
    ok, out = run_adb(["shell", "dumpsys", "activity", "activities"])
    if ok and isinstance(out, str):
        m = re.search(r"(?:topResumedActivity|mResumedActivity)=.*?\s([\w.]+)/", out)
        if m:
            return m.group(1)
    return None


@mcp.tool()
def firetv_button(button: str, times: int = 1) -> str:
    """Press a remote-control button on the Fire TV.

    Args:
        button: One of: up, down, left, right, select, home, back, menu,
            play_pause, play, pause, stop, rewind, fast_forward, next,
            previous, volume_up, volume_down, mute, channel_up, channel_down,
            sleep, wake, power, settings, search, info, guide, captions.
        times: How many times to press it (e.g. down 3 times). Max 20.
    """
    ok, msg = ensure_connected()
    if not ok:
        return msg
    key = button.strip().lower().replace(" ", "_").replace("-", "_")
    if key not in BUTTONS:
        return f"Unknown button '{button}'. Valid: {', '.join(sorted(BUTTONS))}"
    times = max(1, min(int(times), 20))
    code = str(BUTTONS[key])
    for _ in range(times):
        ok, out = run_adb(["shell", "input", "keyevent", code])
        if not ok:
            return f"Button press failed: {out}"
    return f"Pressed {key}" + (f" x{times}" if times > 1 else "")


@mcp.tool()
def firetv_open_app(app: str) -> str:
    """Open (switch to) an app on the Fire TV.

    Args:
        app: A friendly name (e.g. 'Netflix', 'Prime Video', 'YouTube',
            'Disney+', 'Hulu', 'Max', 'Spotify', 'Plex', 'Pluto TV') or an
            Android package name (e.g. 'com.netflix.ninja'). Use
            firetv_list_apps to see what is installed.
    """
    ok, msg = ensure_connected()
    if not ok:
        return msg
    name = app.strip().lower()
    package = APPS.get(name) or (app.strip() if "." in app else None)
    if package and not re.fullmatch(r"[A-Za-z][\w]*(\.[A-Za-z0-9_]+)+", package):
        return f"'{app}' is not a valid Android package name."
    if not package:
        # try a fuzzy match against installed packages
        ok2, out = run_adb(["shell", "pm", "list", "packages"])
        if ok2 and isinstance(out, str):
            simplified = re.sub(r"[^a-z0-9]", "", name)
            for line in out.splitlines():
                pkg = line.replace("package:", "").strip()
                if simplified and simplified in re.sub(r"[^a-z0-9]", "", pkg):
                    package = pkg
                    break
    if not package:
        return (
            f"Could not figure out which app '{app}' is. "
            "Call firetv_list_apps and pick the right package name."
        )
    ok, out = run_adb(
        ["shell", "monkey", "-p", package, "-c",
         "android.intent.category.LAUNCHER", "1"]
    )
    if ok and isinstance(out, str) and "No activities found" not in out:
        return f"Opened {package}"
    # Fallback: LEANBACK_LAUNCHER category used by many TV apps
    ok, out = run_adb(
        ["shell", "monkey", "-p", package, "-c",
         "android.intent.category.LEANBACK_LAUNCHER", "1"]
    )
    if ok and isinstance(out, str) and "No activities found" not in out:
        return f"Opened {package}"
    return f"Could not launch {package}: {out}"


@mcp.tool()
def firetv_list_apps(include_system: bool = False) -> str:
    """List apps installed on the Fire TV (package names).

    Args:
        include_system: Also include pre-installed system packages.
    """
    ok, msg = ensure_connected()
    if not ok:
        return msg
    args = ["shell", "pm", "list", "packages"]
    if not include_system:
        args.append("-3")
    ok, out = run_adb(args)
    if not ok or not isinstance(out, str):
        return f"Failed to list apps: {out}"
    pkgs = sorted(line.replace("package:", "").strip() for line in out.splitlines() if line.strip())
    return "\n".join(pkgs) if pkgs else "No third-party apps found (try include_system=true)."


@mcp.tool()
def firetv_type_text(text: str) -> str:
    """Type text into whatever text field is focused on the Fire TV
    (e.g. a search box). Focus the field first with d-pad navigation.

    Args:
        text: The text to type. Letters, numbers, and spaces work best.
    """
    ok, msg = ensure_connected()
    if not ok:
        return msg
    safe = re.sub(r"[^\w\s@.\-]", "", text).replace(" ", "%s")
    if not safe:
        return "Nothing typeable in that text."
    ok, out = run_adb(["shell", "input", "text", safe])
    return f"Typed: {text}" if ok else f"Typing failed: {out}"


@mcp.tool()
def firetv_screenshot():
    """Take a screenshot of what's currently on the TV so you can see the
    screen and navigate menus visually. Note: DRM-protected video (e.g. a
    playing Netflix stream) appears black, but menus and guides are visible.
    """
    ok, msg = ensure_connected()
    if not ok:
        return msg
    ok, data = run_adb(["exec-out", "screencap", "-p"], binary=True)
    if not ok or not isinstance(data, (bytes, bytearray)) or len(data) < 100:
        return f"Screenshot failed: {data if isinstance(data, str) else 'no image data returned'}"
    return Image(data=bytes(data), format="png")


@mcp.tool()
def firetv_disconnect() -> str:
    """Disconnect from the Fire TV (does not turn the TV off)."""
    ok, out = run_adb(["disconnect"])
    return "Disconnected." if ok else f"Disconnect said: {out}"


if __name__ == "__main__":
    mcp.run()
