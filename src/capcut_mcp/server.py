"""
CapCut MCP Server — Main entry point.

An MCP (Model Context Protocol) server that gives AI assistants
the ability to create and edit CapCut video projects by reading
and writing CapCut's local draft_content.json files.

Usage:
    python -m capcut_mcp.server         # Run with stdio transport
    capcut-mcp                           # Run via installed entry point
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastmcp import FastMCP

from .config import get_drafts_folder, discover_drafts_folder
from .draft_manager import DraftManager
from .tools.project import register_project_tools
from .tools.media import register_media_tools
from .tools.text import register_text_tools
from .tools.audio import register_audio_tools
from .tools.timeline import register_timeline_tools

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("capcut_mcp")

# ---------------------------------------------------------------------------
# Server setup
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "CapCut MCP Server",
    instructions=(
        "An MCP server for automating CapCut video editing. "
        "Create projects, import media, add text/subtitles, manage audio, "
        "and edit timelines — all through AI-powered tools."
    ),
)

# Initialize the draft manager
drafts_folder = get_drafts_folder()
manager = DraftManager(drafts_folder)

# ---------------------------------------------------------------------------
# Register all tool groups
# ---------------------------------------------------------------------------

register_project_tools(mcp, manager)
register_media_tools(mcp, manager)
register_text_tools(mcp, manager)
register_audio_tools(mcp, manager)
register_timeline_tools(mcp, manager)

# ---------------------------------------------------------------------------
# Resources — read-only data for AI context
# ---------------------------------------------------------------------------

@mcp.resource("capcut://config/drafts-folder")
def get_drafts_folder_resource() -> str:
    """Returns the path to the CapCut drafts folder being used."""
    return str(manager.drafts_folder)


@mcp.resource("capcut://config/status")
def get_server_status() -> str:
    """Returns the server status and configuration summary."""
    projects = manager.list_projects()
    folder_exists = manager.drafts_folder.is_dir()
    return (
        f"CapCut MCP Server Status\n"
        f"========================\n"
        f"Drafts folder: {manager.drafts_folder}\n"
        f"Folder exists: {folder_exists}\n"
        f"Projects found: {len(projects)}\n"
        f"CAPCUT_DRAFTS_PATH env: {os.environ.get('CAPCUT_DRAFTS_PATH', '(not set)')}\n"
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    """Run the MCP server."""
    logger.info("Starting CapCut MCP Server")
    logger.info("Drafts folder: %s", manager.drafts_folder)

    projects = manager.list_projects()
    logger.info("Found %d existing project(s)", len(projects))

    mcp.run()


if __name__ == "__main__":
    main()
