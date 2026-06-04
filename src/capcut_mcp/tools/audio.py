"""
MCP Tools — Audio management.

Tools for adding audio tracks, adjusting volume, and muting.
"""

from __future__ import annotations

import os
from pathlib import Path

from ..config import ms_to_us, us_to_ms, us_to_seconds
from ..draft_manager import DraftManager


AUDIO_EXTENSIONS = {".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a", ".wma"}


def _get_audio_duration_us(file_path: str) -> int:
    """
    Get audio file duration in microseconds.

    Tries ffprobe first, falls back to a 60-second default.
    """
    try:
        import subprocess
        import json as _json
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
            info = _json.loads(result.stdout)
            duration_s = float(info["format"]["duration"])
            return int(duration_s * 1_000_000)
    except (FileNotFoundError, KeyError, ValueError, subprocess.TimeoutExpired):
        pass

    return 60_000_000  # 60 seconds default


def register_audio_tools(mcp, manager: DraftManager):
    """Register all audio tools with the MCP server."""

    @mcp.tool()
    def add_audio(
        project_name: str,
        file_path: str,
        start_ms: float = 0,
        volume: float = 1.0,
        trim_start_ms: float = 0,
        trim_end_ms: float = -1,
    ) -> str:
        """
        Add an audio file (music, sound effect, voiceover) to the project.

        Args:
            project_name: Name of the CapCut project.
            file_path: Absolute path to the audio file (MP3, WAV, AAC, FLAC, etc.).
            start_ms: Where to place the audio on the timeline (ms). Default 0.
            volume: Volume level from 0.0 (silent) to 1.0 (full). Default 1.0.
            trim_start_ms: Start trim in the source audio (ms). Default 0.
            trim_end_ms: End trim in the source audio (ms). Use -1 for full duration.

        The audio is placed on a separate audio track (not the main video track).
        """
        if not os.path.isfile(file_path):
            return f"❌ File not found: {file_path}"

        try:
            draft = manager.load_draft(project_name)
        except FileNotFoundError:
            return f"❌ Project not found: '{project_name}'"

        audio_track = manager.get_or_create_track(draft, "audio")

        # Duration
        full_duration_us = _get_audio_duration_us(file_path)
        source_start_us = ms_to_us(trim_start_ms)
        if trim_end_ms >= 0:
            source_duration_us = ms_to_us(trim_end_ms) - source_start_us
        else:
            source_duration_us = full_duration_us - source_start_us

        target_start_us = ms_to_us(start_ms)

        # Create material
        mat = manager.add_audio_material(draft, file_path, full_duration_us)

        # Create speed and fade materials
        speed_mat = manager.add_speed_material(draft, speed=1.0)
        fade_mat = manager.add_audio_fade_material(draft)

        # Create clip
        clip = manager.create_clip(
            material_id=mat.id,
            clip_type="audio",
            source_start_us=source_start_us,
            source_duration_us=source_duration_us,
            target_start_us=target_start_us,
            target_duration_us=source_duration_us,
            extra_material_refs=[speed_mat.id, fade_mat.id],
            volume=volume,
        )
        audio_track.segments.append(clip)

        manager.recalculate_duration(draft)
        manager.save_draft(project_name, draft)

        return (
            f"✅ Audio added to '{project_name}'\n\n"
            f"   File: {Path(file_path).name}\n"
            f"   Position: {us_to_seconds(target_start_us):.2f}s\n"
            f"   Duration: {us_to_seconds(source_duration_us):.2f}s\n"
            f"   Volume: {volume:.0%}\n"
            f"   Segment ID: {clip.id}"
        )

    @mcp.tool()
    def set_volume(
        project_name: str,
        segment_id: str,
        volume: float,
    ) -> str:
        """
        Adjust the volume of a specific clip (video or audio).

        Args:
            project_name: Name of the CapCut project.
            segment_id: ID of the segment to adjust.
            volume: Volume level from 0.0 (silent) to 1.0 (full volume).
                    Values above 1.0 will boost volume.
        """
        try:
            draft = manager.load_draft(project_name)
        except FileNotFoundError:
            return f"❌ Project not found: '{project_name}'"

        result = manager.find_segment_by_id(draft, segment_id)
        if not result:
            return f"❌ Segment not found: {segment_id}"

        track, segment = result
        old_volume = segment.volume
        segment.volume = max(0.0, volume)

        manager.save_draft(project_name, draft)

        return (
            f"✅ Volume updated for segment {segment_id[:8]}…\n"
            f"   {old_volume:.0%} → {volume:.0%}"
        )

    @mcp.tool()
    def mute_track(
        project_name: str,
        track_index: int,
    ) -> str:
        """
        Mute all clips on a specific track.

        Args:
            project_name: Name of the CapCut project.
            track_index: The track number (0-based). Use get_project_info to see tracks.

        Sets volume to 0 for every segment on the track.
        """
        try:
            draft = manager.load_draft(project_name)
        except FileNotFoundError:
            return f"❌ Project not found: '{project_name}'"

        if track_index < 0 or track_index >= len(draft.tracks):
            return f"❌ Invalid track index: {track_index}. Project has {len(draft.tracks)} tracks."

        track = draft.tracks[track_index]
        muted_count = 0
        for seg in track.segments:
            seg.volume = 0.0
            muted_count += 1

        manager.save_draft(project_name, draft)

        return (
            f"✅ Muted track {track_index} [{track.type}]\n"
            f"   {muted_count} segment(s) set to 0% volume"
        )

    @mcp.tool()
    def unmute_track(
        project_name: str,
        track_index: int,
        volume: float = 1.0,
    ) -> str:
        """
        Unmute (restore volume on) all clips on a specific track.

        Args:
            project_name: Name of the CapCut project.
            track_index: The track number (0-based).
            volume: Volume level to set (default 1.0 = 100%).
        """
        try:
            draft = manager.load_draft(project_name)
        except FileNotFoundError:
            return f"❌ Project not found: '{project_name}'"

        if track_index < 0 or track_index >= len(draft.tracks):
            return f"❌ Invalid track index: {track_index}. Project has {len(draft.tracks)} tracks."

        track = draft.tracks[track_index]
        for seg in track.segments:
            seg.volume = volume

        manager.save_draft(project_name, draft)

        return (
            f"✅ Unmuted track {track_index} [{track.type}]\n"
            f"   All segments set to {volume:.0%} volume"
        )
