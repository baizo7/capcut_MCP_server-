"""
MCP Tools — Media import and management.

Tools for adding videos, images, and batch importing media to the timeline.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from ..config import ms_to_us, us_to_ms, us_to_seconds
from ..draft_manager import DraftManager


# Common media file extensions
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv", ".m4v"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".tiff", ".svg"}
MEDIA_EXTENSIONS = VIDEO_EXTENSIONS | IMAGE_EXTENSIONS


def _get_media_duration_us(file_path: str) -> int:
    """
    Estimate media duration in microseconds.

    For images, returns a default 5-second duration.
    For videos, tries to read duration using available methods,
    falling back to a 10-second default.
    """
    ext = Path(file_path).suffix.lower()

    if ext in IMAGE_EXTENSIONS:
        return 5_000_000  # 5 seconds default for images

    # Try to get video duration using ffprobe if available
    try:
        import subprocess
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                file_path,
            ],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            import json
            info = json.loads(result.stdout)
            duration_s = float(info["format"]["duration"])
            return int(duration_s * 1_000_000)
    except (FileNotFoundError, KeyError, ValueError, subprocess.TimeoutExpired):
        pass

    # Default fallback: 10 seconds for video
    return 10_000_000


def register_media_tools(mcp, manager: DraftManager):
    """Register all media import tools with the MCP server."""

    @mcp.tool()
    def add_video(
        project_name: str,
        file_path: str,
        position_ms: float = -1,
        trim_start_ms: float = 0,
        trim_end_ms: float = -1,
    ) -> str:
        """
        Add a video file to the project's main video track.

        Args:
            project_name: Name of the CapCut project.
            file_path: Absolute path to the video file on disk.
            position_ms: Where to place the clip on the timeline (milliseconds).
                         Use -1 to append after the last clip.
            trim_start_ms: Start trim point in the source video (ms). Default 0.
            trim_end_ms: End trim point in the source video (ms). Use -1 for full duration.

        The video file must exist on disk. CapCut will reference it by path.
        """
        # Validate file exists
        if not os.path.isfile(file_path):
            return f"❌ File not found: {file_path}"

        try:
            draft = manager.load_draft(project_name)
        except FileNotFoundError:
            return f"❌ Project not found: '{project_name}'"

        # Get or create the main video track
        video_track = manager.get_or_create_track(draft, "video", 0)

        # Determine source duration
        full_duration_us = _get_media_duration_us(file_path)

        # Handle trimming
        source_start_us = ms_to_us(trim_start_ms)
        if trim_end_ms >= 0:
            source_duration_us = ms_to_us(trim_end_ms) - source_start_us
        else:
            source_duration_us = full_duration_us - source_start_us

        # Handle timeline position
        if position_ms < 0:
            target_start_us = manager.get_track_end_position(video_track)
        else:
            target_start_us = ms_to_us(position_ms)

        # Create material
        mat = manager.add_video_material(draft, file_path, full_duration_us)

        # Create speed material (required by CapCut)
        speed_mat = manager.add_speed_material(draft, speed=1.0)

        # Create the clip
        clip = manager.create_clip(
            material_id=mat.id,
            clip_type="video",
            source_start_us=source_start_us,
            source_duration_us=source_duration_us,
            target_start_us=target_start_us,
            target_duration_us=source_duration_us,
            extra_material_refs=[speed_mat.id],
        )
        video_track.segments.append(clip)

        # Recalculate total duration
        manager.recalculate_duration(draft)

        # Save
        manager.save_draft(project_name, draft)

        return (
            f"✅ Video added to project '{project_name}'\n\n"
            f"   File: {Path(file_path).name}\n"
            f"   Position: {us_to_seconds(target_start_us):.2f}s\n"
            f"   Duration: {us_to_seconds(source_duration_us):.2f}s\n"
            f"   Segment ID: {clip.id}\n"
            f"   Material ID: {mat.id}"
        )

    @mcp.tool()
    def add_image(
        project_name: str,
        file_path: str,
        duration_ms: float = 5000,
        position_ms: float = -1,
    ) -> str:
        """
        Add an image to the project's video track as a still clip.

        Args:
            project_name: Name of the CapCut project.
            file_path: Absolute path to the image file.
            duration_ms: How long to show the image (ms). Default 5000 (5 seconds).
            position_ms: Where to place it on the timeline (ms). Use -1 to append.

        Supports JPG, PNG, BMP, GIF, WebP, TIFF, SVG.
        """
        if not os.path.isfile(file_path):
            return f"❌ File not found: {file_path}"

        try:
            draft = manager.load_draft(project_name)
        except FileNotFoundError:
            return f"❌ Project not found: '{project_name}'"

        video_track = manager.get_or_create_track(draft, "video", 0)
        duration_us = ms_to_us(duration_ms)

        if position_ms < 0:
            target_start_us = manager.get_track_end_position(video_track)
        else:
            target_start_us = ms_to_us(position_ms)

        mat = manager.add_video_material(
            draft, file_path, duration_us, is_photo=True
        )
        speed_mat = manager.add_speed_material(draft, speed=1.0)

        clip = manager.create_clip(
            material_id=mat.id,
            clip_type="video",
            source_start_us=0,
            source_duration_us=duration_us,
            target_start_us=target_start_us,
            target_duration_us=duration_us,
            extra_material_refs=[speed_mat.id],
        )
        video_track.segments.append(clip)
        manager.recalculate_duration(draft)
        manager.save_draft(project_name, draft)

        return (
            f"✅ Image added to project '{project_name}'\n\n"
            f"   File: {Path(file_path).name}\n"
            f"   Position: {us_to_seconds(target_start_us):.2f}s\n"
            f"   Duration: {us_to_seconds(duration_us):.2f}s\n"
            f"   Segment ID: {clip.id}"
        )

    @mcp.tool()
    def add_media_batch(
        project_name: str,
        folder_path: str,
        pattern: str = "*",
        image_duration_ms: float = 5000,
    ) -> str:
        """
        Import all media files from a folder into the project sequentially.

        Args:
            project_name: Name of the CapCut project.
            folder_path: Absolute path to the folder containing media files.
            pattern: Glob pattern to filter files (e.g., "*.mp4", "*.jpg"). Default "*" for all media.
            image_duration_ms: Duration for each image clip (ms). Default 5000.

        Files are added in alphabetical order, one after another on the timeline.
        Supported: MP4, MOV, AVI, MKV, WebM, JPG, PNG, BMP, GIF, WebP.
        """
        folder = Path(folder_path)
        if not folder.is_dir():
            return f"❌ Folder not found: {folder_path}"

        try:
            draft = manager.load_draft(project_name)
        except FileNotFoundError:
            return f"❌ Project not found: '{project_name}'"

        video_track = manager.get_or_create_track(draft, "video", 0)

        # Collect matching media files
        if pattern == "*":
            files = sorted(
                f for f in folder.iterdir()
                if f.is_file() and f.suffix.lower() in MEDIA_EXTENSIONS
            )
        else:
            files = sorted(folder.glob(pattern))
            files = [f for f in files if f.is_file() and f.suffix.lower() in MEDIA_EXTENSIONS]

        if not files:
            return f"❌ No media files found in '{folder_path}' matching pattern '{pattern}'"

        added = []
        for file_path in files:
            ext = file_path.suffix.lower()
            is_photo = ext in IMAGE_EXTENSIONS

            if is_photo:
                duration_us = ms_to_us(image_duration_ms)
            else:
                duration_us = _get_media_duration_us(str(file_path))

            target_start_us = manager.get_track_end_position(video_track)

            mat = manager.add_video_material(
                draft, str(file_path), duration_us, is_photo=is_photo
            )
            speed_mat = manager.add_speed_material(draft, speed=1.0)

            clip = manager.create_clip(
                material_id=mat.id,
                clip_type="video",
                source_start_us=0,
                source_duration_us=duration_us,
                target_start_us=target_start_us,
                target_duration_us=duration_us,
                extra_material_refs=[speed_mat.id],
            )
            video_track.segments.append(clip)
            added.append(f"   • {file_path.name} ({us_to_seconds(duration_us):.1f}s)")

        manager.recalculate_duration(draft)
        manager.save_draft(project_name, draft)

        total_dur = us_to_seconds(draft.duration)
        return (
            f"✅ Added {len(added)} media file(s) to '{project_name}'\n\n"
            + "\n".join(added)
            + f"\n\n   Total timeline duration: {total_dur:.1f}s"
        )

    @mcp.tool()
    def list_materials(project_name: str) -> str:
        """
        List all materials (assets) registered in a project.

        Args:
            project_name: Name of the CapCut project.

        Shows videos, images, audio clips, and text overlays with their IDs.
        """
        try:
            draft = manager.load_draft(project_name)
        except FileNotFoundError:
            return f"❌ Project not found: '{project_name}'"

        lines = [f"Materials in '{project_name}':\n"]
        m = draft.materials

        if m.videos:
            lines.append(f"🎥 Videos/Images ({len(m.videos)}):")
            for v in m.videos:
                name = Path(v.path).name if v.path else "(no path)"
                lines.append(f"   [{v.type}] {name} — {us_to_seconds(v.duration):.1f}s (id: {v.id[:8]}…)")

        if m.audios:
            lines.append(f"\n🔊 Audio ({len(m.audios)}):")
            for a in m.audios:
                name = Path(a.path).name if a.path else a.name or "(unnamed)"
                lines.append(f"   {name} — {us_to_seconds(a.duration):.1f}s (id: {a.id[:8]}…)")

        if m.texts:
            lines.append(f"\n📝 Text ({len(m.texts)}):")
            for t in m.texts:
                preview = t.base_content[:50] if t.base_content else "(empty)"
                lines.append(f"   \"{preview}\" (id: {t.id[:8]}…)")

        if not m.videos and not m.audios and not m.texts:
            lines.append("   (no materials)")

        return "\n".join(lines)

    @mcp.tool()
    def remove_material(project_name: str, material_id: str) -> str:
        """
        Remove a material and all its segments from the project.

        Args:
            project_name: Name of the CapCut project.
            material_id: The ID of the material to remove (use list_materials to find IDs).

        This removes the material from the registry AND removes any clips
        on the timeline that reference it.
        """
        try:
            draft = manager.load_draft(project_name)
        except FileNotFoundError:
            return f"❌ Project not found: '{project_name}'"

        # Remove from materials
        removed = False
        for mat_list in [draft.materials.videos, draft.materials.audios, draft.materials.texts]:
            for mat in mat_list:
                if mat.id == material_id:
                    mat_list.remove(mat)
                    removed = True
                    break
            if removed:
                break

        if not removed:
            return f"❌ Material not found: {material_id}"

        # Remove segments referencing this material
        segments_removed = 0
        for track in draft.tracks:
            before = len(track.segments)
            track.segments = [s for s in track.segments if s.material_id != material_id]
            segments_removed += before - len(track.segments)

        manager.recalculate_duration(draft)
        manager.save_draft(project_name, draft)

        return (
            f"✅ Removed material {material_id[:8]}… and {segments_removed} segment(s) "
            f"from '{project_name}'"
        )
