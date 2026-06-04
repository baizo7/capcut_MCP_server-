"""
MCP Tools — Project management.

Tools for listing, creating, duplicating, and deleting CapCut projects.
"""

from __future__ import annotations

import json
from typing import Any

from ..config import CANVAS_PRESETS, us_to_ms, us_to_seconds
from ..draft_manager import DraftManager


def _format_duration(ms: float) -> str:
    """Format milliseconds as human-readable duration."""
    total_seconds = ms / 1000
    minutes = int(total_seconds // 60)
    seconds = total_seconds % 60
    if minutes > 0:
        return f"{minutes}m {seconds:.1f}s"
    return f"{seconds:.1f}s"


def register_project_tools(mcp, manager: DraftManager):
    """Register all project management tools with the MCP server."""

    @mcp.tool()
    def list_projects() -> str:
        """
        List all CapCut projects found on this computer.

        Returns a summary of each project including name, duration,
        resolution, FPS, and number of tracks.
        """
        projects = manager.list_projects()
        if not projects:
            return (
                "No CapCut projects found.\n\n"
                f"Drafts folder: {manager.drafts_folder}\n"
                "You can create a new project with the create_project tool."
            )

        lines = [f"Found {len(projects)} CapCut project(s):\n"]
        for p in projects:
            duration_str = _format_duration(p["duration_ms"]) if p["duration_ms"] > 0 else "empty"
            lines.append(
                f"  📁 {p['name']}\n"
                f"     Duration: {duration_str} | "
                f"Resolution: {p['width']}x{p['height']} | "
                f"FPS: {p['fps']} | "
                f"Tracks: {p['track_count']}\n"
                f"     Path: {p['path']}\n"
            )

        return "\n".join(lines)

    @mcp.tool()
    def get_project_info(project_name: str) -> str:
        """
        Get detailed information about a CapCut project.

        Args:
            project_name: The name of the project to inspect.

        Returns detailed info including all tracks, materials, and segments.
        """
        try:
            draft = manager.load_draft(project_name)
        except FileNotFoundError:
            return f"❌ Project not found: '{project_name}'. Use list_projects to see available projects."

        lines = [
            f"📁 Project: {draft.name or project_name}",
            f"   ID: {draft.id}",
            f"   Duration: {_format_duration(us_to_ms(draft.duration))}",
            f"   FPS: {draft.fps}",
            f"   Canvas: {draft.canvas_config.width}x{draft.canvas_config.height} ({draft.canvas_config.ratio})",
            "",
            f"📊 Materials:",
            f"   Videos/Images: {len(draft.materials.videos)}",
            f"   Audio clips: {len(draft.materials.audios)}",
            f"   Text overlays: {len(draft.materials.texts)}",
            "",
            f"🎬 Tracks ({len(draft.tracks)}):",
        ]

        for i, track in enumerate(draft.tracks):
            lines.append(f"   Track {i} [{track.type}]: {len(track.segments)} segment(s)")
            for j, seg in enumerate(track.segments):
                start_s = us_to_seconds(seg.target_timerange.start)
                dur_s = us_to_seconds(seg.target_timerange.duration)
                lines.append(
                    f"      Segment {j}: {start_s:.2f}s → {start_s + dur_s:.2f}s "
                    f"(id: {seg.id[:8]}…, material: {seg.material_id[:8]}…)"
                )

        return "\n".join(lines)

    @mcp.tool()
    def create_project(
        name: str,
        preset: str = "landscape",
        width: int | None = None,
        height: int | None = None,
        fps: float = 30.0,
    ) -> str:
        """
        Create a new empty CapCut project.

        Args:
            name: Name for the new project.
            preset: Canvas preset — one of: landscape (1920x1080), portrait (1080x1920),
                    square (1080x1080), youtube, tiktok, instagram_reel, instagram_post.
            width: Custom canvas width (overrides preset if provided).
            height: Custom canvas height (overrides preset if provided).
            fps: Frames per second (default 30).

        Returns confirmation with the project details.
        """
        # Resolve dimensions
        canvas = CANVAS_PRESETS.get(preset, CANVAS_PRESETS["landscape"])
        w = width or canvas["width"]
        h = height or canvas["height"]
        ratio = canvas["ratio"]

        if width and height:
            # Compute ratio from custom dimensions
            from math import gcd
            g = gcd(w, h)
            ratio = f"{w // g}:{h // g}"

        try:
            draft = manager.create_project(name=name, width=w, height=h, fps=fps, ratio=ratio)
        except FileExistsError:
            return f"❌ A project with a similar name already exists. Try a different name."

        return (
            f"✅ Project created successfully!\n\n"
            f"   Name: {name}\n"
            f"   Resolution: {w}x{h} ({ratio})\n"
            f"   FPS: {fps}\n"
            f"   ID: {draft.id}\n\n"
            f"You can now add media, text, and audio to this project."
        )

    @mcp.tool()
    def duplicate_project(source_name: str, new_name: str) -> str:
        """
        Duplicate an existing CapCut project.

        Args:
            source_name: Name of the project to copy.
            new_name: Name for the duplicated project.

        Creates a full copy of the project with a new ID.
        """
        try:
            draft = manager.duplicate_project(source_name, new_name)
        except FileNotFoundError:
            return f"❌ Source project not found: '{source_name}'."

        return (
            f"✅ Project duplicated!\n\n"
            f"   Original: {source_name}\n"
            f"   New copy: {new_name}\n"
            f"   New ID: {draft.id}"
        )

    @mcp.tool()
    def delete_project(project_name: str, confirm: bool = False) -> str:
        """
        Delete a CapCut project.

        Args:
            project_name: Name of the project to delete.
            confirm: Must be set to True to actually delete. Safety check.

        ⚠️ This permanently deletes the project folder and all its files.
        """
        if not confirm:
            return (
                f"⚠️ Are you sure you want to delete '{project_name}'?\n"
                f"This action cannot be undone.\n\n"
                f"Call delete_project again with confirm=True to proceed."
            )

        deleted = manager.delete_project(project_name)
        if deleted:
            return f"✅ Project '{project_name}' has been deleted."
        return f"❌ Project not found: '{project_name}'."

    @mcp.tool()
    def list_canvas_presets() -> str:
        """
        List available canvas size presets for creating new projects.

        Shows all preset names and their resolutions.
        """
        lines = ["Available canvas presets:\n"]
        for name, config in CANVAS_PRESETS.items():
            lines.append(f"  • {name}: {config['width']}x{config['height']} ({config['ratio']})")
        return "\n".join(lines)
