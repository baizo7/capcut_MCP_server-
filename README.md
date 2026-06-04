# 🎬 CapCut MCP Server

An **MCP (Model Context Protocol) server** that gives AI assistants full control over CapCut video editing projects. Create projects, import media, add text/subtitles, manage audio, and edit timelines — all through AI-powered tools.

## How It Works

```text
AI Assistant  ──MCP Protocol──▶  CapCut MCP Server  ──Read/Write JSON──▶  CapCut Draft Files
                                  (Python/FastMCP)                          (draft_content.json)
```

CapCut stores every project as a folder with a `draft_content.json` file. This MCP server reads and writes those files directly. You edit via the AI, then open the project in CapCut to preview and export.

## Quick Start

### 1. Install

```bash
# Clone your repository
git clone https://github.com/baizo7/capcut_MCP_server-.git
cd capcut_MCP_server-

# Using pip
pip install -e ".[cli]"

# Or using uv (recommended)
uv pip install -e .
```

### 2. Configure your MCP client

#### Gemini IDE / Antigravity

On Windows, open your Gemini MCP configuration file located at:
`%USERPROFILE%\.gemini\config\mcp_config.json`

Add this to your `mcpServers` object:

```json
{
  "mcpServers": {
    "capcut": {
      "command": "python",
      "args": ["-m", "capcut_mcp.server"],
      "env": {
        "CAPCUT_DRAFTS_PATH": "C:\\Users\\LENOVO\\AppData\\Local\\CapCut\\User Data\\Projects\\com.lveditor.draft"
      }
    }
  }
}
```
*Note: After saving, restart the IDE for the new server to boot up.*

#### Claude Desktop

Add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "capcut": {
      "command": "python",
      "args": ["-m", "capcut_mcp.server"]
    }
  }
}
```

#### Cursor IDE

Add to `.cursor/mcp.json` in your project:

```json
{
  "mcpServers": {
    "capcut": {
      "command": "python",
      "args": ["-m", "capcut_mcp.server"]
    }
  }
}
```

### 3. Start editing!

Once configured, your AI assistant can use commands like:
- *"Create a new TikTok project called 'Summer Vibes'"*
- *"Import all videos from D:\footage\vacation and add them to the timeline"*
- *"Add subtitles: 'Hello!' at 0-2s and 'Welcome!' at 2-5s"*
- *"Trim the first clip to start at 3 seconds"*

---

## 🛑 Important Limitations & Workarounds

### 1. Windows Store Python Sandbox
If you are running the MCP server using Python installed from the **Microsoft Store** (which is common in Gemini IDE and Cursor), Windows automatically sandboxes writes to `AppData\Local`.
* **The Issue:** The AI will create projects perfectly, but Windows hides them from CapCut.
* **The Fix:** We built an automatic "Sandbox Escape" into the server using PowerShell! However, for best results, we highly recommend changing CapCut's default save location (Settings -> Project -> Save to) to your `Documents` folder, and updating your `CAPCUT_DRAFTS_PATH` environment variable to match it.

### 2. CapCut Does Not "Hot-Reload"
Because we are editing the raw JSON save files on your hard drive behind CapCut's back, CapCut does not instantly update its screen while you are actively editing a timeline.
* **To see changes:** You must click the "X" in CapCut to return to the Home screen, then click the project again to force CapCut to reload the timeline from the hard drive.
* **For new projects:** Simply switch tabs (e.g., from "Space" to "Home") to refresh the project list.

---

## Configuration

| Environment Variable | Description | Default |
|---|---|---|
| `CAPCUT_DRAFTS_PATH` | Path to your CapCut drafts folder | Auto-discovered |

### Auto-discovery

The server automatically checks these locations for CapCut projects:
- `%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft`
- `%LOCALAPPDATA%\CapCut\User Data\Drafts`

---

## Available Tools (25+)

### 📁 Project Management
| Tool | Description |
|---|---|
| `list_projects` | List all CapCut projects on this computer |
| `get_project_info` | Detailed project info: tracks, materials, segments |
| `create_project` | Create a new empty project (with canvas presets) |
| `duplicate_project` | Clone a project as a template |
| `delete_project` | Delete a project (requires confirmation) |
| `list_canvas_presets` | Show available canvas sizes (landscape, portrait, etc.) |

### 🎥 Media Import
| Tool | Description |
|---|---|
| `add_video` | Import a video file to the timeline |
| `add_image` | Add an image as a still clip |
| `add_media_batch` | Batch-import all media from a folder |
| `list_materials` | List all assets in a project |
| `remove_material` | Remove an asset and its timeline clips |

### 📝 Text & Subtitles
| Tool | Description |
|---|---|
| `add_text` | Add a text overlay at a specific time |
| `add_subtitles` | Bulk-add subtitles from a structured list |
| `update_text_style` | Change font, color, size, alignment |
| `update_text_content` | Change the text content |

### 🔊 Audio
| Tool | Description |
|---|---|
| `add_audio` | Add background music or sound effects |
| `set_volume` | Adjust volume of a specific clip |
| `mute_track` | Mute all clips on a track |
| `unmute_track` | Restore volume on a muted track |

### ✂️ Timeline Editing
| Tool | Description |
|---|---|
| `trim_clip` | Trim a clip's start/end point |
| `split_clip` | Split a clip into two parts at a timestamp |
| `move_clip` | Move a clip to a new timeline position |
| `delete_clip` | Remove a clip from the timeline |
| `reorder_clips` | Arrange clips sequentially with optional gaps |
| `set_clip_speed` | Change playback speed (slow-mo, fast-forward) |

---

## Safety Features

- **Automatic backups**: Every edit creates a `.backup` of the draft before modifying
- **Non-destructive**: Delete operations require explicit confirmation
- **Validation**: All file paths are verified before import

---

## Development

```bash
# Install in development mode
pip install -e ".[dev]"

# Run tests
python -m pytest tests/ -v

# Test with MCP Inspector (browser-based)
python -m fastmcp dev src/capcut_mcp/server.py
```

---

## Important Notes

⚠️ **Unofficial**: This server reverse-engineers CapCut's project format. It is not affiliated with ByteDance.

⚠️ **Backups**: The server automatically backs up projects before modification, but always keep your own backups of important projects.

⚠️ **ffprobe**: For accurate video/audio duration detection, install [FFmpeg](https://ffmpeg.org/download.html) and ensure `ffprobe` is on your PATH. Without it, the server uses default duration estimates.