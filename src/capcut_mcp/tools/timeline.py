"""
MCP Tools — Timeline editing.

Tools for trimming, splitting, moving, deleting, and reordering clips.
"""

from __future__ import annotations

from ..config import ms_to_us, us_to_ms, us_to_seconds
from ..draft_manager import DraftManager
from ..models import Clip, TimeRange, _new_id


def register_timeline_tools(mcp, manager: DraftManager):
    """Register all timeline editing tools with the MCP server."""

    @mcp.tool()
    def trim_clip(
        project_name: str,
        segment_id: str,
        new_start_ms: float | None = None,
        new_end_ms: float | None = None,
    ) -> str:
        """
        Trim a clip by adjusting its start and/or end point.

        Args:
            project_name: Name of the CapCut project.
            segment_id: ID of the segment to trim.
            new_start_ms: New start time relative to the source material (ms).
                          Trims the beginning of the clip.
            new_end_ms: New end time relative to the source material (ms).
                        Trims the end of the clip.

        Only the provided values are applied. Omit a value to keep it unchanged.
        """
        try:
            draft = manager.load_draft(project_name)
        except FileNotFoundError:
            return f"❌ Project not found: '{project_name}'"

        result = manager.find_segment_by_id(draft, segment_id)
        if not result:
            return f"❌ Segment not found: {segment_id}"

        track, segment = result
        old_source_start = segment.source_timerange.start
        old_source_dur = segment.source_timerange.duration
        old_target_dur = segment.target_timerange.duration

        if new_start_ms is not None:
            new_start_us = ms_to_us(new_start_ms)
            # Adjust: if we move the source start forward, duration shrinks
            delta = new_start_us - segment.source_timerange.start
            segment.source_timerange.start = new_start_us
            segment.source_timerange.duration -= delta
            segment.target_timerange.duration -= delta

        if new_end_ms is not None:
            new_end_us = ms_to_us(new_end_ms)
            new_duration = new_end_us - segment.source_timerange.start
            segment.source_timerange.duration = new_duration
            segment.target_timerange.duration = new_duration

        manager.recalculate_duration(draft)
        manager.save_draft(project_name, draft)

        new_dur_s = us_to_seconds(segment.target_timerange.duration)
        return (
            f"✅ Trimmed segment {segment_id[:8]}…\n"
            f"   New duration: {new_dur_s:.2f}s\n"
            f"   Source range: {us_to_seconds(segment.source_timerange.start):.2f}s "
            f"→ {us_to_seconds(segment.source_timerange.start + segment.source_timerange.duration):.2f}s"
        )

    @mcp.tool()
    def split_clip(
        project_name: str,
        segment_id: str,
        at_ms: float,
    ) -> str:
        """
        Split a clip into two parts at a specific timestamp.

        Args:
            project_name: Name of the CapCut project.
            segment_id: ID of the segment to split.
            at_ms: The timeline position (ms) at which to split the clip.
                   Must be within the clip's time range.

        Creates two segments: the original (trimmed to end at the split point)
        and a new segment starting at the split point.
        """
        try:
            draft = manager.load_draft(project_name)
        except FileNotFoundError:
            return f"❌ Project not found: '{project_name}'"

        result = manager.find_segment_by_id(draft, segment_id)
        if not result:
            return f"❌ Segment not found: {segment_id}"

        track, segment = result
        split_us = ms_to_us(at_ms)

        seg_start = segment.target_timerange.start
        seg_end = seg_start + segment.target_timerange.duration

        if split_us <= seg_start or split_us >= seg_end:
            return (
                f"❌ Split point {at_ms}ms is outside the clip's range "
                f"({us_to_ms(seg_start)}ms → {us_to_ms(seg_end)}ms)"
            )

        # Calculate split point relative to source
        offset_into_clip = split_us - seg_start
        source_split_point = segment.source_timerange.start + offset_into_clip

        # First part: original segment, trimmed at the end
        original_source_dur = offset_into_clip
        segment.source_timerange.duration = original_source_dur
        segment.target_timerange.duration = original_source_dur

        # Second part: new segment starting at split point
        remaining_dur = seg_end - split_us
        new_clip = Clip(
            id=_new_id(),
            type=segment.type,
            material_id=segment.material_id,
            source_timerange=TimeRange(
                start=source_split_point,
                duration=remaining_dur,
            ),
            target_timerange=TimeRange(
                start=split_us,
                duration=remaining_dur,
            ),
            extra_material_refs=list(segment.extra_material_refs),
            volume=segment.volume,
        )

        # Insert the new clip right after the original
        seg_index = track.segments.index(segment)
        track.segments.insert(seg_index + 1, new_clip)

        manager.save_draft(project_name, draft)

        return (
            f"✅ Split segment {segment_id[:8]}… at {at_ms}ms\n\n"
            f"   Part 1: {us_to_seconds(seg_start):.2f}s → {us_to_seconds(split_us):.2f}s "
            f"(id: {segment.id[:8]}…)\n"
            f"   Part 2: {us_to_seconds(split_us):.2f}s → {us_to_seconds(seg_end):.2f}s "
            f"(id: {new_clip.id[:8]}…)"
        )

    @mcp.tool()
    def move_clip(
        project_name: str,
        segment_id: str,
        new_position_ms: float,
    ) -> str:
        """
        Move a clip to a different position on the timeline.

        Args:
            project_name: Name of the CapCut project.
            segment_id: ID of the segment to move.
            new_position_ms: New start position on the timeline (ms).

        This only changes the timeline position, not the source content.
        """
        try:
            draft = manager.load_draft(project_name)
        except FileNotFoundError:
            return f"❌ Project not found: '{project_name}'"

        result = manager.find_segment_by_id(draft, segment_id)
        if not result:
            return f"❌ Segment not found: {segment_id}"

        track, segment = result
        old_pos = segment.target_timerange.start
        segment.target_timerange.start = ms_to_us(new_position_ms)

        manager.recalculate_duration(draft)
        manager.save_draft(project_name, draft)

        return (
            f"✅ Moved segment {segment_id[:8]}…\n"
            f"   {us_to_seconds(old_pos):.2f}s → {us_to_seconds(ms_to_us(new_position_ms)):.2f}s"
        )

    @mcp.tool()
    def delete_clip(
        project_name: str,
        segment_id: str,
    ) -> str:
        """
        Delete a clip from the timeline.

        Args:
            project_name: Name of the CapCut project.
            segment_id: ID of the segment to delete.

        Removes the segment from its track. The associated material is kept
        in case other clips reference it. Use remove_material to also clean
        up unused materials.
        """
        try:
            draft = manager.load_draft(project_name)
        except FileNotFoundError:
            return f"❌ Project not found: '{project_name}'"

        result = manager.find_segment_by_id(draft, segment_id)
        if not result:
            return f"❌ Segment not found: {segment_id}"

        track, segment = result
        track.segments.remove(segment)

        manager.recalculate_duration(draft)
        manager.save_draft(project_name, draft)

        return f"✅ Deleted segment {segment_id[:8]}… from track [{track.type}]"

    @mcp.tool()
    def reorder_clips(
        project_name: str,
        track_index: int,
        gap_ms: float = 0,
    ) -> str:
        """
        Reorder clips on a track so they play sequentially without gaps.

        Args:
            project_name: Name of the CapCut project.
            track_index: The track number (0-based).
            gap_ms: Gap to insert between clips (ms). Default 0 (no gap).

        Clips are placed one after another in their current order.
        Useful after deleting or moving clips to clean up the timeline.
        """
        try:
            draft = manager.load_draft(project_name)
        except FileNotFoundError:
            return f"❌ Project not found: '{project_name}'"

        if track_index < 0 or track_index >= len(draft.tracks):
            return f"❌ Invalid track index: {track_index}"

        track = draft.tracks[track_index]
        if not track.segments:
            return f"ℹ️ Track {track_index} [{track.type}] has no segments to reorder."

        # Sort by current start position
        track.segments.sort(key=lambda s: s.target_timerange.start)

        # Reposition sequentially
        gap_us = ms_to_us(gap_ms)
        current_pos = 0
        for seg in track.segments:
            seg.target_timerange.start = current_pos
            current_pos += seg.target_timerange.duration + gap_us

        manager.recalculate_duration(draft)
        manager.save_draft(project_name, draft)

        total = us_to_seconds(current_pos - gap_us) if track.segments else 0
        return (
            f"✅ Reordered {len(track.segments)} clip(s) on track {track_index} [{track.type}]\n"
            f"   Gap: {gap_ms}ms between clips\n"
            f"   Total duration: {total:.2f}s"
        )

    @mcp.tool()
    def set_clip_speed(
        project_name: str,
        segment_id: str,
        speed: float,
    ) -> str:
        """
        Change the playback speed of a clip.

        Args:
            project_name: Name of the CapCut project.
            segment_id: ID of the segment to adjust.
            speed: Playback speed multiplier. 1.0 = normal, 2.0 = 2x fast, 0.5 = half speed.

        Adjusts the clip's timeline duration based on the new speed.
        A 10s clip at 2x speed becomes 5s on the timeline.
        """
        if speed <= 0:
            return "❌ Speed must be greater than 0."

        try:
            draft = manager.load_draft(project_name)
        except FileNotFoundError:
            return f"❌ Project not found: '{project_name}'"

        result = manager.find_segment_by_id(draft, segment_id)
        if not result:
            return f"❌ Segment not found: {segment_id}"

        track, segment = result
        old_speed = segment.speed
        segment.speed = speed

        # Adjust timeline duration based on speed change
        source_dur = segment.source_timerange.duration
        new_target_dur = int(source_dur / speed)
        segment.target_timerange.duration = new_target_dur

        # Update speed material if referenced
        for ref_id in segment.extra_material_refs:
            for speed_mat in draft.materials.speeds:
                if speed_mat.id == ref_id:
                    speed_mat.speed = speed
                    break

        manager.recalculate_duration(draft)
        manager.save_draft(project_name, draft)

        return (
            f"✅ Speed changed for segment {segment_id[:8]}…\n"
            f"   {old_speed}x → {speed}x\n"
            f"   New timeline duration: {us_to_seconds(new_target_dur):.2f}s"
        )
