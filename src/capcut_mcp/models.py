"""
Pydantic models for the CapCut draft_content.json schema.

These models represent the reverse-engineered structure of CapCut project
files. All time values are stored in MICROSECONDS (μs).
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from pydantic import BaseModel, Field


def _new_id() -> str:
    """Generate a new UUID string for CapCut entities."""
    return str(uuid.uuid4()).upper()


# ---------------------------------------------------------------------------
# Time range
# ---------------------------------------------------------------------------

class TimeRange(BaseModel):
    """A time span in microseconds, used for source and target ranges."""
    start: int = 0
    duration: int = 0


# ---------------------------------------------------------------------------
# Canvas configuration
# ---------------------------------------------------------------------------

class CanvasConfig(BaseModel):
    """Canvas (output) resolution settings."""
    width: int = 1920
    height: int = 1080
    ratio: str = "16:9"


# ---------------------------------------------------------------------------
# Materials — the asset registry
# ---------------------------------------------------------------------------

class VideoMaterial(BaseModel):
    """A video or image material entry."""
    id: str = Field(default_factory=_new_id)
    path: str = ""
    type: str = "video"  # "video" or "photo"
    width: int = 0
    height: int = 0
    duration: int = 0  # microseconds
    material_name: str = ""
    category_id: str = ""
    category_name: str = "local"
    check_flag: int = 63
    crop: dict[str, Any] = Field(default_factory=lambda: {
        "lower_left_x": 0.0,
        "lower_left_y": 1.0,
        "lower_right_x": 1.0,
        "lower_right_y": 1.0,
        "upper_left_x": 0.0,
        "upper_left_y": 0.0,
        "upper_right_x": 1.0,
        "upper_right_y": 0.0,
    })
    extra_type_option: int = 0
    formula_id: str = ""
    freeze: Any = None
    has_audio: bool = True
    intensifies_audio_path: str = ""
    intensifies_path: str = ""
    is_ai_generate_content: bool = False
    is_copyright: bool = False
    is_text_edit_overdub: bool = False
    is_unified_beauty_mode: bool = False
    local_id: str = ""
    local_material_id: str = ""
    material_id: str = ""
    material_url: str = ""
    media_path: str = ""
    music_id: str = ""
    object_locked: Any = None
    origin_material_id: str = ""
    query: str = ""
    request_id: str = ""
    reverse_intensifies_path: str = ""
    reverse_path: str = ""
    smart_motion: Any = None
    source: int = 0
    source_platform: int = 0
    stable: dict[str, Any] = Field(default_factory=lambda: {
        "matrix_path": "",
        "stable_level": 0,
        "time_range": {"duration": 0, "start": 0},
    })
    team_id: str = ""
    video_algorithm: dict[str, Any] = Field(default_factory=lambda: {
        "algorithms": [],
        "deflicker": None,
        "motion_blur_config": None,
        "noise_reduction": None,
        "path": "",
        "quality_enhance": None,
    })


class AudioMaterial(BaseModel):
    """An audio material entry (music, sound effects, voiceover)."""
    id: str = Field(default_factory=_new_id)
    path: str = ""
    duration: int = 0  # microseconds
    type: str = "extract_music"
    category_id: str = ""
    category_name: str = "local"
    check_flag: int = 63
    effect_id: str = ""
    formula_id: str = ""
    intensifies_path: str = ""
    local_material_id: str = ""
    material_id: str = ""
    material_name: str = ""
    material_url: str = ""
    music_id: str = ""
    name: str = ""
    query: str = ""
    request_id: str = ""
    resource_id: str = ""
    search_id: str = ""
    source: int = 0
    source_platform: int = 0
    team_id: str = ""


class TextMaterialContent(BaseModel):
    """Content definition for a text material."""
    text: str = ""
    styles: list[dict[str, Any]] = Field(default_factory=lambda: [{
        "range": [0, 0],
        "font": {"id": "", "path": "", "name": ""},
        "size": 8.0,
        "fill": {"content": {"solid": {"color": [1.0, 1.0, 1.0, 1.0]}}},
        "bold": False,
        "italic": False,
        "underline": False,
        "useLetterColor": True,
    }])


class TextMaterial(BaseModel):
    """A text overlay / subtitle material."""
    id: str = Field(default_factory=_new_id)
    type: str = "subtitle"
    add_type: int = 0
    alignment: int = 1  # 0=left, 1=center, 2=right
    background_alpha: float = 1.0
    background_color: str = ""
    background_height: float = 0.14
    background_horizontal_offset: float = 0.0
    background_round_radius: float = 0.0
    background_style: int = 0
    background_vertical_offset: float = 0.0
    background_width: float = 0.14
    base_content: str = ""
    bold_width: float = 0.0
    border_alpha: float = 1.0
    border_color: str = ""
    border_width: float = 0.08
    caption_template_info: dict[str, Any] = Field(default_factory=lambda: {
        "category_id": "", "category_name": "",
        "effect_id": "", "is_new": False,
        "path": "", "request_id": "", "resource_id": "",
    })
    check_flag: int = 7
    combo_info: dict[str, Any] = Field(default_factory=lambda: {"text_templates": []})
    content: str = '{"text":""}'
    fixed_height: float = -1.0
    fixed_width: float = -1.0
    font_category_id: str = ""
    font_category_name: str = ""
    font_id: str = ""
    font_name: str = ""
    font_path: str = ""
    font_resource_id: str = ""
    font_size: float = 15.0
    font_source_platform: int = 0
    font_team_id: str = ""
    font_title: str = "Font"
    font_url: str = ""
    fonts: list[Any] = Field(default_factory=list)
    force_apply_line_max_width: bool = False
    global_alpha: float = 1.0
    group_id: str = ""
    has_shadow: bool = False
    initial_scale: float = 1.0
    inner_padding: float = -1.0
    is_rich_text: bool = False
    italic_degree: int = 0
    ktv_color: str = ""
    language: str = ""
    layer_weight: int = 1
    letter_spacing: float = 0.0
    line_feed: int = 1
    line_max_width: float = 0.82
    line_spacing: float = 0.02
    multi_language_current: str = "none"
    name: str = ""
    original_size: list[Any] = Field(default_factory=list)
    preset_category: str = ""
    preset_category_id: str = ""
    preset_has_set_alignment: bool = False
    preset_id: str = ""
    preset_index: int = 0
    preset_name: str = ""
    recognize_task_id: str = ""
    recognize_type: int = 0
    relevance_segment: list[Any] = Field(default_factory=list)
    shadow_alpha: float = 0.9
    shadow_angle: float = -45.0
    shadow_color: str = ""
    shadow_distance: float = 0.04
    shadow_point: dict[str, float] = Field(default_factory=lambda: {"x": 0.0, "y": 0.0})
    shadow_smoothing: float = 0.45
    shape_clip_x: bool = False
    shape_clip_y: bool = False
    source_from: str = ""
    style_name: str = ""
    sub_type: int = 0
    subtitle_keywords: Any = None
    text_alpha: float = 1.0
    text_color: str = "#FFFFFF"
    text_curve: Any = None
    text_preset_resource_id: str = ""
    text_size: int = 30
    text_to_audio_ids: list[Any] = Field(default_factory=list)
    tts_auto_update: bool = False
    typesetting: int = 0
    underline: bool = False
    underline_offset: float = 0.22
    underline_width: float = 0.05
    use_effect_default_color: bool = True
    words: dict[str, Any] = Field(default_factory=lambda: {
        "end_time": [], "start_time": [], "text": [],
    })


class SpeedConfig(BaseModel):
    """Speed/playback configuration for a segment."""
    curve_speed: Any = None
    id: str = Field(default_factory=_new_id)
    mode: int = 0
    speed: float = 1.0
    type: str = "speed"


class AudioFade(BaseModel):
    """Audio fade in/out configuration."""
    id: str = Field(default_factory=_new_id)
    fade_in_duration: int = 0
    fade_out_duration: int = 0
    type: str = "audio_fade"


class VolumeConfig(BaseModel):
    """Volume settings for a segment."""
    id: str = Field(default_factory=_new_id)
    volume: float = 1.0
    type: str = "volume"


# ---------------------------------------------------------------------------
# Materials container
# ---------------------------------------------------------------------------

class Materials(BaseModel):
    """Container for all materials (assets) in a project."""
    audio_balances: list[Any] = Field(default_factory=list)
    audio_effects: list[Any] = Field(default_factory=list)
    audio_fades: list[AudioFade] = Field(default_factory=list)
    audios: list[AudioMaterial] = Field(default_factory=list)
    beats: list[Any] = Field(default_factory=list)
    canvases: list[dict[str, Any]] = Field(default_factory=list)
    chromas: list[Any] = Field(default_factory=list)
    color_curves: list[Any] = Field(default_factory=list)
    digital_humans: list[Any] = Field(default_factory=list)
    drafts: list[Any] = Field(default_factory=list)
    effects: list[Any] = Field(default_factory=list)
    flowers: list[Any] = Field(default_factory=list)
    green_screens: list[Any] = Field(default_factory=list)
    handwrites: list[Any] = Field(default_factory=list)
    hsl: list[Any] = Field(default_factory=list)
    images: list[Any] = Field(default_factory=list)
    log_color_wheels: list[Any] = Field(default_factory=list)
    loudnesses: list[Any] = Field(default_factory=list)
    manual_deformations: list[Any] = Field(default_factory=list)
    masks: list[Any] = Field(default_factory=list)
    material_animations: list[dict[str, Any]] = Field(default_factory=list)
    material_colors: list[Any] = Field(default_factory=list)
    multi_language_refs: list[Any] = Field(default_factory=list)
    placeholders: list[Any] = Field(default_factory=list)
    plugin_effects: list[Any] = Field(default_factory=list)
    primary_color_wheels: list[Any] = Field(default_factory=list)
    realtime_denoises: list[Any] = Field(default_factory=list)
    smart_crops: list[Any] = Field(default_factory=list)
    smart_relights: list[Any] = Field(default_factory=list)
    sound_channel_mappings: list[Any] = Field(default_factory=list)
    speeds: list[SpeedConfig] = Field(default_factory=list)
    stickers: list[Any] = Field(default_factory=list)
    tail_leaders: list[Any] = Field(default_factory=list)
    text_templates: list[Any] = Field(default_factory=list)
    texts: list[TextMaterial] = Field(default_factory=list)
    transitions: list[Any] = Field(default_factory=list)
    video_effects: list[Any] = Field(default_factory=list)
    video_trackings: list[Any] = Field(default_factory=list)
    videos: list[VideoMaterial] = Field(default_factory=list)
    vocal_beautifys: list[Any] = Field(default_factory=list)
    vocal_separations: list[Any] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Segments — clips on the timeline
# ---------------------------------------------------------------------------

class Clip(BaseModel):
    """
    A segment (clip) on a track.
    Links a material to a position on the timeline.
    """
    id: str = Field(default_factory=_new_id)
    type: str = "video"  # "video", "audio", "text"
    material_id: str = ""
    source_timerange: TimeRange = Field(default_factory=TimeRange)
    target_timerange: TimeRange = Field(default_factory=TimeRange)
    cartoon: bool = False
    clip: dict[str, Any] = Field(default_factory=lambda: {
        "alpha": 1.0,
        "flip": {"horizontal": False, "vertical": False},
        "rotation": 0.0,
        "scale": {"x": 1.0, "y": 1.0},
        "transform": {"x": 0.0, "y": 0.0},
    })
    common_keyframes: list[Any] = Field(default_factory=list)
    enable_adjust: bool = True
    enable_color_correct_adjust: bool = False
    enable_color_curves: bool = True
    enable_color_match_adjust: bool = False
    enable_color_wheels: bool = True
    enable_lut: bool = True
    enable_smart_color_adjust: bool = False
    extra_material_refs: list[str] = Field(default_factory=list)
    group_id: str = ""
    hdr_settings: dict[str, Any] = Field(default_factory=lambda: {"intensity": 1.0, "mode": 1, "nits": 1000})
    intensifies_audio: bool = False
    is_batch_replace: bool = False
    is_placeholder: bool = False
    is_tone_modify: bool = False
    keyframe_refs: list[Any] = Field(default_factory=list)
    last_nonzero_volume: float = 1.0
    nle_cursor_position: int = 0
    position: str = ""
    render_index: int = 0
    responsive_layout: dict[str, Any] = Field(default_factory=lambda: {
        "enable": False, "horizontal_pos_layout": 0,
        "size_layout": 0, "target_follow": "",
        "vertical_pos_layout": 0,
    })
    reverse: bool = False
    speed: float = 1.0
    template_id: str = ""
    template_scene: str = "default"
    track_attribute: int = 0
    track_render_index: int = 0
    uniform_scale: dict[str, Any] = Field(default_factory=lambda: {"on": True, "value": 1.0})
    visible: bool = True
    volume: float = 1.0


# ---------------------------------------------------------------------------
# Tracks
# ---------------------------------------------------------------------------

class Track(BaseModel):
    """A timeline track (video, audio, or text lane)."""
    id: str = Field(default_factory=_new_id)
    type: str = "video"  # "video", "audio", "text"
    attribute: int = 0
    flag: int = 0
    is_default_name: bool = True
    name: str = ""
    segments: list[Clip] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Top-level draft content
# ---------------------------------------------------------------------------

class DraftContent(BaseModel):
    """
    Top-level representation of a CapCut draft_content.json file.
    This is the master project structure.
    """
    id: str = Field(default_factory=_new_id)
    name: str = ""
    duration: int = 0  # microseconds
    fps: float = 30.0
    canvas_config: CanvasConfig = Field(default_factory=CanvasConfig)
    tracks: list[Track] = Field(default_factory=list)
    materials: Materials = Field(default_factory=Materials)
    # Additional metadata
    create_time: int = 0
    update_time: int = 0
    version: int = 360000
    platform: dict[str, Any] = Field(default_factory=lambda: {
        "app_id": 359289,
        "app_source": "cc",
        "app_version": "5.0.0",
        "device_id": "",
        "hard_disk_id": "",
        "installation_id": "",
        "os": "windows",
        "os_version": "10.0",
    })
    cover: str = ""
    color_space: int = 0
    config: dict[str, Any] = Field(default_factory=lambda: {
        "adjust_max_index": 1,
        "attachment_info": [],
        "combination_max_index": 1,
        "export_range": None,
        "extract_audio_last_index": 0,
        "lyrics_recognition_id": "",
        "lyrics_sync": True,
        "lyrics_taskinfo": [],
        "maintrack_adsorb": True,
        "material_save_mode": 0,
        "original_sound_last_index": 0,
        "record_audio_last_index": 0,
        "sticker_max_index": 1,
        "subtitle_keywords_config": None,
        "subtitle_recognition_id": "",
        "subtitle_sync": True,
        "subtitle_taskinfo": [],
        "system_font_list": [],
        "video_mute": False,
        "zoom_info_params": None,
    })
    extra_info: Any = None
    free_render_index_mode_on: bool = False
    group_container: Any = None
    keyframe_graph_list: list[Any] = Field(default_factory=list)
    keyframes: dict[str, Any] = Field(default_factory=lambda: {"adjusts": [], "audios": [], "effects": [], "filters": [], "handwrites": [], "stickers": [], "texts": [], "videos": []})
    last_modified_platform: dict[str, Any] = Field(default_factory=lambda: {"app_id": 359289, "app_source": "cc", "app_version": "5.0.0", "device_id": "", "os": "windows", "os_version": "10.0"})
    multi_camera_group_info: Any = None
    mutable_config: Any = None
    record_audio: Any = None
    source: str = "default"
    static_cover_image_path: str = ""
    template_info: Any = None
    top_graphic: str = ""
