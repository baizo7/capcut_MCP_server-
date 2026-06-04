"""
MCP Tools — Text and subtitle management.

Tools for adding text overlays, bulk subtitles, and styling text.
"""

from __future__ import annotations

import json
from typing import Any

from ..config import ms_to_us, us_to_ms, us_to_seconds
from ..draft_manager import DraftManager


def register_text_tools(mcp, manager: DraftManager):
    """Register all text/subtitle tools with the MCP server."""

    @mcp.tool()
    def add_text(
        project_name: str,
        content: str,
        start_ms: float = 0,
        duration_ms: float = 3000,
        font_size: float = 15.0,
        color: str = "#FFFFFF",
        alignment: int = 1,
    ) -> str:
        """
        Add a text overlay to the project at a specific time.

        Args:
            project_name: Name of the CapCut project.
            content: The text content to display.
            start_ms: When the text appears on the timeline (milliseconds).
            duration_ms: How long the text stays visible (ms). Default 3000 (3s).
            font_size: Font size. Default 15.0.
            color: Text color as hex string (e.g., "#FFFFFF" for white, "#FF0000" for red).
            alignment: Text alignment — 0=left, 1=center, 2=right. Default 1 (center).

        The text will appear as an overlay on top of any video content.
        """
        try:
            draft = manager.load_draft(project_name)
        except FileNotFoundError:
            return f"❌ Project not found: '{project_name}'"

        text_track = manager.get_or_create_track(draft, "text")

        # Create text material
        mat = manager.add_text_material(draft, content, font_size, color)
        mat.alignment = alignment

        # Create clip
        start_us = ms_to_us(start_ms)
        duration_us = ms_to_us(duration_ms)

        clip = manager.create_clip(
            material_id=mat.id,
            clip_type="text",
            source_start_us=0,
            source_duration_us=duration_us,
            target_start_us=start_us,
            target_duration_us=duration_us,
        )
        text_track.segments.append(clip)

        manager.recalculate_duration(draft)
        manager.save_draft(project_name, draft)

        return (
            f"✅ Text added to '{project_name}'\n\n"
            f"   Content: \"{content}\"\n"
            f"   Time: {us_to_seconds(start_us):.2f}s → {us_to_seconds(start_us + duration_us):.2f}s\n"
            f"   Color: {color} | Size: {font_size} | Align: {['left', 'center', 'right'][alignment]}\n"
            f"   Segment ID: {clip.id}"
        )

    @mcp.tool()
    def add_subtitles(
        project_name: str,
        subtitles: list[dict[str, Any]],
        font_size: float = 12.0,
        color: str = "#FFFFFF",
    ) -> str:
        """
        Add multiple subtitle entries to the project in bulk.

        Args:
            project_name: Name of the CapCut project.
            subtitles: A list of subtitle objects, each with:
                       - "text": The subtitle text (required)
                       - "start_ms": Start time in milliseconds (required)
                       - "end_ms": End time in milliseconds (required)
            font_size: Font size for all subtitles. Default 12.0.
            color: Text color hex for all subtitles. Default "#FFFFFF".

        Example subtitles list:
        [
            {"text": "Hello world!", "start_ms": 0, "end_ms": 2000},
            {"text": "Welcome to my video.", "start_ms": 2000, "end_ms": 5000}
        ]
        """
        try:
            draft = manager.load_draft(project_name)
        except FileNotFoundError:
            return f"❌ Project not found: '{project_name}'"

        if not subtitles:
            return "❌ No subtitles provided. Pass a list of {text, start_ms, end_ms} objects."

        text_track = manager.get_or_create_track(draft, "text")
        added = 0
        errors = []

        for i, sub in enumerate(subtitles):
            text = sub.get("text", "")
            start_ms = sub.get("start_ms", 0)
            end_ms = sub.get("end_ms", 0)

            if not text:
                errors.append(f"   Subtitle {i}: missing 'text'")
                continue
            if end_ms <= start_ms:
                errors.append(f"   Subtitle {i}: end_ms must be > start_ms")
                continue

            duration_ms = end_ms - start_ms
            mat = manager.add_text_material(draft, text, font_size, color)

            start_us = ms_to_us(start_ms)
            duration_us = ms_to_us(duration_ms)

            clip = manager.create_clip(
                material_id=mat.id,
                clip_type="text",
                source_start_us=0,
                source_duration_us=duration_us,
                target_start_us=start_us,
                target_duration_us=duration_us,
            )
            text_track.segments.append(clip)
            added += 1

        manager.recalculate_duration(draft)
        manager.save_draft(project_name, draft)

        result = f"✅ Added {added} subtitle(s) to '{project_name}'"
        if errors:
            result += "\n\n⚠️ Skipped entries:\n" + "\n".join(errors)
        return result

    @mcp.tool()
    def update_text_style(
        project_name: str,
        segment_id: str,
        font_size: float | None = None,
        color: str | None = None,
        alignment: int | None = None,
        bold: bool | None = None,
        italic: bool | None = None,
    ) -> str:
        """
        Update the styling of an existing text overlay.

        Args:
            project_name: Name of the CapCut project.
            segment_id: ID of the text segment to update (from get_project_info or add_text).
            font_size: New font size (optional).
            color: New text color hex (optional).
            alignment: New alignment — 0=left, 1=center, 2=right (optional).
            bold: Set bold style (optional).
            italic: Set italic style (optional).

        Only the provided parameters will be updated; others remain unchanged.
        """
        try:
            draft = manager.load_draft(project_name)
        except FileNotFoundError:
            return f"❌ Project not found: '{project_name}'"

        # Find the segment
        result = manager.find_segment_by_id(draft, segment_id)
        if not result:
            return f"❌ Segment not found: {segment_id}"

        track, segment = result
        if segment.type != "text":
            return f"❌ Segment {segment_id[:8]}… is not a text segment (type: {segment.type})"

        # Find the corresponding text material
        text_mat = None
        for t in draft.materials.texts:
            if t.id == segment.material_id:
                text_mat = t
                break

        if not text_mat:
            return f"❌ Text material not found for segment {segment_id[:8]}…"

        # Apply updates
        changes = []
        if font_size is not None:
            text_mat.font_size = font_size
            text_mat.text_size = int(font_size * 2)
            changes.append(f"font_size={font_size}")
        if color is not None:
            text_mat.text_color = color
            changes.append(f"color={color}")
        if alignment is not None:
            text_mat.alignment = alignment
            changes.append(f"alignment={['left', 'center', 'right'][alignment]}")

        manager.save_draft(project_name, draft)

        return (
            f"✅ Updated text style for segment {segment_id[:8]}…\n"
            f"   Changes: {', '.join(changes) if changes else 'none'}"
        )

    @mcp.tool()
    def update_text_content(
        project_name: str,
        segment_id: str,
        new_text: str,
    ) -> str:
        """
        Update the text content of an existing text overlay.

        Args:
            project_name: Name of the CapCut project.
            segment_id: ID of the text segment to update.
            new_text: The new text content.
        """
        try:
            draft = manager.load_draft(project_name)
        except FileNotFoundError:
            return f"❌ Project not found: '{project_name}'"

        result = manager.find_segment_by_id(draft, segment_id)
        if not result:
            return f"❌ Segment not found: {segment_id}"

        track, segment = result

        # Find text material
        text_mat = None
        for t in draft.materials.texts:
            if t.id == segment.material_id:
                text_mat = t
                break

        if not text_mat:
            return f"❌ Text material not found for segment {segment_id[:8]}…"

        old_text = text_mat.base_content
        text_mat.base_content = new_text
        text_mat.content = json.dumps({"text": new_text})

        manager.save_draft(project_name, draft)

        return (
            f"✅ Text updated for segment {segment_id[:8]}…\n"
            f"   Old: \"{old_text}\"\n"
            f"   New: \"{new_text}\""
        )
