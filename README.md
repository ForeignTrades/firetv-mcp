<h1 align="center">firetv-mcp</h1>

<p align="center">
  <b>Turn Claude into a remote control for your Amazon Fire TV.</b><br/>
  A single-file MCP server that lets an AI agent change apps, press buttons, type into search boxes, and even <i>see</i> your TV screen — all over your home Wi-Fi.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/protocol-MCP-8A2BE2" alt="MCP" />
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License" />
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey" alt="Platforms" />
</p>

---

Once it's set up, you just talk:

> "Open Netflix on the TV" · "Pause it" · "Channel up" · "Go back to the home screen" · "Open YouTube and search for jazz piano" · "Take a screenshot of the TV and tell me what's on"

## How it works

```
You (Claude chat) ──► firetv-mcp (this script, on your computer) ──► ADB over Wi-Fi ──► Fire TV
```

Fire TV devices running Fire OS support [ADB debugging over the network](https://developer.amazon.com/docs/fire-tv/connecting-adb-to-device.html) — the same developer connection Amazon documents officially. This server wraps that connection in [Model Context Protocol](https://modelcontextprotocol.io) tools, so any MCP client (Claude Desktop, Claude Code, or your own agent) can drive the TV in plain language.

The screenshot tool is what makes it a real *agent* rather than a macro pad: the AI can look at the screen, see where the focus is, and navigate menus step by step.

## Tools

| Tool | What it does |
|---|---|
| `firetv_connect` | Connect to the Fire TV by IP (remembered afterwards, auto-reconnects) |
| `firetv_status` | Connection check, device model, power state, foreground app |
| `firetv_button` | Any remote button: d-pad, home, back, play/pause, rewind, fast-forward, channel up/down, volume, mute, sleep/wake, and more — with repeat ("down 3 times") |
| `firetv_open_app` | Launch apps by friendly name (Netflix, Prime Video, YouTube, Disney+, Hulu, Max, Apple TV, Spotify, Plex, Pluto TV, …) or any package name, with fuzzy matching |
| `firetv_list_apps` | List installed apps |
| `firetv_type_text` | Type into the focused text field (search boxes) |
| `firetv_screenshot` | Screenshot the TV so the agent can see the UI (DRM video frames appear black; menus are visible) |
| `firetv_disconnect` | Drop the ADB connection |

## Requirements

- A Fire TV device running **Fire OS** (Stick 4K / 4K Max, Cube, and most sticks from recent years). Amazon's newest budget devices run **Vega OS**, which has no ADB and cannot work with this.
- **Python 3.10+** and `pip install mcp`
- **ADB** (Android platform-tools) — [download](https://developer.android.com/tools/releases/platform-tools), or `brew install android-platform-tools` on macOS, `sudo apt install adb` on Linux
- Fire TV and computer on the **same network**

## Quick start

**1. Enable ADB on the Fire TV**

Settings → My Fire TV → About → select your device name **7 times** ("You are now a developer"), then My Fire TV → Developer Options → turn on **ADB Debugging**. Note the IP under About → Network.

**2. Get the server**

```bash
git clone https://github.com/ForeignTrades/firetv-mcp.git
cd firetv-mcp
pip install mcp
```

**3. Register it with your MCP client**

<details>
<summary><b>Claude Desktop</b> (Settings → Developer → Edit Config)</summary>

```json
{
  "mcpServers": {
    "firetv": {
      "command": "python",
      "args": ["/full/path/to/firetv_mcp.py"],
      "env": { "FIRETV_IP": "192.168.1.42" }
    }
  }
}
```

On macOS/Linux use `python3` as the command. Restart the app.
</details>

<details>
<summary><b>Claude Code</b></summary>

```bash
claude mcp add firetv -e FIRETV_IP=192.168.1.42 -- python /full/path/to/firetv_mcp.py
```
</details>

**4. First connection**

Say *"Connect to my Fire TV and check its status."* The TV shows a one-time **Allow USB debugging?** popup — choose **Always allow from this computer**. Done.

## Configuration

| Env var | Purpose |
|---|---|
| `FIRETV_IP` | IP address of the Fire TV. Optional — you can also just tell the agent the IP once; it's saved to `~/.firetv_mcp.json`. |
| `FIRETV_ADB` | Full path to `adb` if it isn't on `PATH`. On Windows, unzipping platform-tools to `C:\platform-tools` is auto-detected. |

## Troubleshooting

- **"adb not found"** — install platform-tools, or set `FIRETV_ADB`.
- **Connection refused** — ADB Debugging off, TV asleep, or different network (guest Wi-Fi is often isolated). Wake the TV once with its physical remote and retry.
- **"unauthorized"** — the Allow-debugging popup is waiting on the TV screen.
- **Connects then drops** — Fire TV closes idle ADB sessions; the server reconnects automatically on the next command.
- **Volume keys do nothing** — your TV may not accept HDMI-CEC volume from the stick.

## Security notes

- With ADB Debugging enabled, **any device on your network** can send commands to the Fire TV. Fine on a trusted home network; don't enable it on shared Wi-Fi. You can toggle it off any time without losing this setup.
- The server runs entirely on your machine and talks only to your TV. No cloud, no telemetry, no accounts. The only thing it stores is the TV's IP address in `~/.firetv_mcp.json`.
- Give the agent the same trust you'd give anyone holding your remote: it can open apps and navigate anything your remote can.
- On Windows, the `FIRETV_ADB` fallback path `C:\platform-tools\adb.exe` sits at the drive root, where default ACLs let any standard local user create files; prefer installing platform-tools under your user profile (or set `FIRETV_ADB` explicitly) if you share this machine with untrusted accounts.

## License

[MIT](LICENSE) — do whatever you like, no warranty.

---

<p align="center"><sub>Header artwork generated with <a href="https://higgsfield.ai">Higgsfield</a>. Not affiliated with Amazon; Fire TV is a trademark of Amazon.com, Inc.</sub></p>
