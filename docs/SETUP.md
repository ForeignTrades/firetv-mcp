# Fire TV Agent — Setup Guide

Turn Claude into a remote control for your Fire TV Stick. Once set up, you can say things like:

> "Open Netflix on the TV" · "Pause it" · "Channel up" · "Go back to the home screen" · "Open YouTube and search for jazz piano" · "Take a screenshot of the TV and tell me what's on screen"

**How it works:** a small program (`firetv_mcp.py`) runs on your laptop and talks to the Fire Stick over your home Wi-Fi using ADB — the same developer connection Amazon documents officially. Claude calls that program as a tool, so Claude is the agent and the script is its hands.

---

## Step 0 — Check your Fire TV is compatible (30 seconds)

On the TV go to **Settings → My Fire TV → About**.

- If you see a **"Developer Options"** entry under My Fire TV (or can unlock it — see Step 1), you're good. All Fire TV Stick 4K / 4K Max, Fire TV Cube, and most sticks from the last several years work.
- Amazon's newest budget devices run **Vega OS**, which has no Developer Options and blocks this method entirely. If your About screen shows "Fire TV Stick HD (2025)" or similar and no Developer Options can be unlocked, this approach won't work on that device.

## Step 1 — Enable ADB on the Fire Stick

1. **Settings → My Fire TV → About** — highlight your device name and press the **select button 7 times**. A message says "You are now a developer."
2. Go back to **My Fire TV → Developer Options** → turn ON **ADB Debugging**.
3. Still in **About → Network**, write down the **IP address** (e.g. `192.168.1.42`).

Tip: in your router settings, reserve that IP for the Fire Stick (DHCP reservation) so it never changes.

## Step 2 — Install the two prerequisites on your laptop

### ADB (Android platform-tools)

- **Windows:** download "SDK Platform-Tools for Windows" from https://developer.android.com/tools/releases/platform-tools — unzip it to `C:\platform-tools`. (The script looks there automatically; no PATH editing needed.)
- **Mac:** in Terminal: `brew install android-platform-tools` (install Homebrew first from https://brew.sh if needed).
- **Linux:** `sudo apt install adb`

### Python + the MCP library

- **Windows:** install Python from https://python.org (check "Add python.exe to PATH" during install), then in Command Prompt: `pip install mcp`
- **Mac/Linux:** Python 3 is usually present; run `pip3 install mcp` (add `--break-system-packages` if pip refuses).

## Step 3 — Put the server file somewhere permanent

Save `firetv_mcp.py` in a folder that won't move, e.g.:

- Windows: `C:\Users\<you>\firetv\firetv_mcp.py`
- Mac: `/Users/<you>/firetv/firetv_mcp.py`

## Step 4 — Register it with Claude

### Option A: Claude Desktop app (recommended)

Open **Settings → Developer → Edit Config** (this opens `claude_desktop_config.json`) and add:

**Windows:**
```json
{
  "mcpServers": {
    "firetv": {
      "command": "python",
      "args": ["C:\\Users\\<you>\\firetv\\firetv_mcp.py"],
      "env": { "FIRETV_IP": "192.168.1.42" }
    }
  }
}
```

**Mac:**
```json
{
  "mcpServers": {
    "firetv": {
      "command": "python3",
      "args": ["/Users/<you>/firetv/firetv_mcp.py"],
      "env": { "FIRETV_IP": "192.168.1.42" }
    }
  }
}
```

Replace the path and IP with yours. If the config file already has an `mcpServers` section, add `"firetv": {...}` inside it. Restart the Claude app.

Bonus: if the desktop app is running, other Claude surfaces can reach the `firetv` tools through the device bridge — so you can text Claude from your phone and it can still change the channel at home.

### Option B: Claude Code (terminal)

```bash
claude mcp add firetv -e FIRETV_IP=192.168.1.42 -- python3 /path/to/firetv_mcp.py
```

(On Windows use `python` instead of `python3`.)

## Step 5 — First connection

In a new Claude chat, say: **"Connect to my Fire TV and check its status."**

The first time, the TV shows an **"Allow USB debugging?"** popup — select **"Always allow from this computer"** and OK. After that it reconnects automatically, and the IP is remembered.

---

## What Claude can do once connected

| You say | What happens |
|---|---|
| "Open Netflix" / "Switch to Hulu" | Launches the app (knows Netflix, Prime Video, YouTube, Disney+, Hulu, Max, Apple TV, Spotify, Plex, Pluto TV, and more — or any installed app by package name) |
| "Channel up" / "Channel down" | Sends channel keys (works inside live-TV apps like Pluto, Sling, YouTube TV) |
| "Pause" / "Play" / "Rewind" / "Skip forward" | Media controls |
| "Go home" / "Go back" / "Down three, then select" | Remote navigation |
| "Search YouTube for cooking videos" | Opens the app, navigates, types the query |
| "What's on the TV right now?" | Takes a screenshot and looks at it |
| "Turn the TV display off / wake it up" | Sleep / wake |
| "Volume up / mute" | Volume keys (on devices that route volume over HDMI-CEC) |

The screenshot tool is what makes it a real *agent*: Claude can look at the screen, see where the cursor is, and navigate menus step by step — not just fire blind commands. (One limit: DRM-protected video frames come back black, so Claude can see menus and guides but not the movie itself.)

## Troubleshooting

- **"adb not found"** — install platform-tools (Step 2). On Windows, keeping it at `C:\platform-tools` means zero configuration; otherwise set `FIRETV_ADB` in the `env` block to the full path of `adb.exe`.
- **"Connection refused" / can't connect** — TV asleep or ADB Debugging off; check Developer Options and that both devices are on the same Wi-Fi (guest networks are often isolated). Wake the TV with its physical remote once and retry.
- **"unauthorized"** — the Allow-debugging popup is waiting on the TV screen.
- **Connects then drops** — Fire Sticks close idle ADB sessions; the script reconnects automatically on the next command, so this is usually invisible.
- **Volume buttons do nothing** — your TV may not accept CEC volume from the stick; use the TV's own remote for volume.

## Security note

ADB Debugging means any device on your home Wi-Fi could send commands to the stick. On a normal home network that's a low risk, but don't enable it if you're on shared/untrusted Wi-Fi. You can toggle ADB Debugging off any time in Developer Options without losing this setup.
