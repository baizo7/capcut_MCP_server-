"""
Configuration and path discovery for CapCut MCP Server.

Auto-discovers the CapCut drafts folder on Windows and provides
global settings used throughout the server.
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Time constants — CapCut stores all times in MICROSECONDS
# ---------------------------------------------------------------------------
MICROSECONDS_PER_SECOND = 1_000_000
MICROSECONDS_PER_MS = 1_000

# ---------------------------------------------------------------------------
# Default project settings
# ---------------------------------------------------------------------------
DEFAULT_FPS = 30.0
DEFAULT_WIDTH = 1920
DEFAULT_HEIGHT = 1080
DEFAULT_RATIO = "16:9"

# Canvas presets
CANVAS_PRESETS = {
    "landscape": {"width": 1920, "height": 1080, "ratio": "16:9"},
    "portrait": {"width": 1080, "height": 1920, "ratio": "9:16"},
    "square": {"width": 1080, "height": 1080, "ratio": "1:1"},
    "youtube": {"width": 1920, "height": 1080, "ratio": "16:9"},
    "tiktok": {"width": 1080, "height": 1920, "ratio": "9:16"},
    "instagram_reel": {"width": 1080, "height": 1920, "ratio": "9:16"},
    "instagram_post": {"width": 1080, "height": 1080, "ratio": "1:1"},
}


def ms_to_us(ms: float) -> int:
    """Convert milliseconds to microseconds."""
    return int(ms * MICROSECONDS_PER_MS)


def us_to_ms(us: int) -> float:
    """Convert microseconds to milliseconds."""
    return us / MICROSECONDS_PER_MS


def seconds_to_us(seconds: float) -> int:
    """Convert seconds to microseconds."""
    return int(seconds * MICROSECONDS_PER_SECOND)


def us_to_seconds(us: int) -> float:
    """Convert microseconds to seconds."""
    return us / MICROSECONDS_PER_SECOND


def _get_candidate_draft_paths() -> list[Path]:
    """Return a list of candidate paths where CapCut drafts may live."""
    local_appdata = os.environ.get("LOCALAPPDATA", "")
    candidates = []

    if local_appdata:
        base = Path(local_appdata)
        candidates.extend([
            base / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft",
            base / "CapCut" / "User Data" / "Drafts",
        ])

    return candidates


def discover_drafts_folder() -> Path | None:
    """
    Auto-discover the CapCut drafts folder on this machine.

    Checks:
      1. CAPCUT_DRAFTS_PATH environment variable (user override)
      2. Known default Windows locations

    Returns the first existing path, or None if nothing is found.
    """
    # 1. User override via env var
    env_path = os.environ.get("CAPCUT_DRAFTS_PATH")
    if env_path:
        p = Path(env_path)
        if p.is_dir():
            logger.info("Using CAPCUT_DRAFTS_PATH: %s", p)
            return p
        else:
            logger.warning("CAPCUT_DRAFTS_PATH is set but does not exist: %s", p)

    # 2. Auto-discovery
    for candidate in _get_candidate_draft_paths():
        if candidate.is_dir():
            logger.info("Auto-discovered drafts folder: %s", candidate)
            return candidate

    logger.warning(
        "Could not auto-discover CapCut drafts folder. "
        "Set CAPCUT_DRAFTS_PATH environment variable to your drafts directory."
    )
    return None


def get_drafts_folder() -> Path:
    """
    Get the CapCut drafts folder, creating a fallback if none is found.

    If no existing folder is discovered, creates a default one at
    %LOCALAPPDATA%/CapCut/User Data/Projects/com.lveditor.draft
    so the server can still create new projects.
    """
    folder = discover_drafts_folder()
    if folder:
        return folder

    # Create a default location
    local_appdata = os.environ.get("LOCALAPPDATA", "")
    if local_appdata:
        default = Path(local_appdata) / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft"
    else:
        default = Path.home() / "CapCut_Projects"

    default.mkdir(parents=True, exist_ok=True)
    logger.info("Created default drafts folder: %s", default)
    return default
