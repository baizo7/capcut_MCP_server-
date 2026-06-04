"""
Draft Manager — Core engine for reading, writing, and backing up CapCut projects.

Handles all filesystem interactions with CapCut's draft folder structure:
  project_folder/
    draft_content.json    ← the main project data
    draft_meta_info.json  ← lightweight metadata
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import time
from pathlib import Path
from typing import Any

from .config import get_drafts_folder, ms_to_us, us_to_ms
from .models import (
    AudioFade,
    AudioMaterial,
    CanvasConfig,
    Clip,
    DraftContent,
    Materials,
    SpeedConfig,
    TextMaterial,
    TimeRange,
    Track,
    VideoMaterial,
    VolumeConfig,
    _new_id,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_json(path: Path) -> dict[str, Any]:
    """Read and parse a JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    """Write a dict to a JSON file with pretty formatting."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _now_timestamp() -> int:
    """Current time as an integer timestamp (microseconds since epoch)."""
    return int(time.time() * 1_000_000)


# ---------------------------------------------------------------------------
# DraftManager
# ---------------------------------------------------------------------------

class DraftManager:
    """
    Manages CapCut project draft files on disk.

    Provides CRUD operations on CapCut projects by reading and writing
    the draft_content.json and draft_meta_info.json files.
    """

    def __init__(self, drafts_folder: Path | None = None):
        self.drafts_folder = drafts_folder or get_drafts_folder()
        logger.info("DraftManager initialized with folder: %s", self.drafts_folder)

    # ------------------------------------------------------------------
    # Project listing & discovery
    # ------------------------------------------------------------------

    def list_projects(self) -> list[dict[str, Any]]:
        """
        List all CapCut projects found in the drafts folder.

        Returns a list of dicts with basic project info:
        name, id, path, duration_ms, resolution, fps, last_modified.
        """
        projects = []
        if not self.drafts_folder.is_dir():
            return projects

        for entry in sorted(self.drafts_folder.iterdir()):
            if not entry.is_dir():
                continue

            draft_file = entry / "draft_content.json"
            meta_file = entry / "draft_meta_info.json"

            if not draft_file.exists():
                continue

            try:
                # Read meta info first (lightweight)
                meta = {}
                if meta_file.exists():
                    meta = _read_json(meta_file)

                # Read just enough from draft_content for the listing
                draft_data = _read_json(draft_file)
                canvas = draft_data.get("canvas_config", {})

                projects.append({
                    "name": meta.get("draft_name", entry.name),
                    "id": draft_data.get("id", entry.name),
                    "folder_name": entry.name,
                    "path": str(entry),
                    "duration_ms": us_to_ms(draft_data.get("duration", 0)),
                    "width": canvas.get("width", 0),
                    "height": canvas.get("height", 0),
                    "fps": draft_data.get("fps", 30),
                    "last_modified": meta.get("tm_draft_modified", 0),
                    "track_count": len(draft_data.get("tracks", [])),
                })
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Skipping invalid project %s: %s", entry.name, e)

        return projects

    def get_project_folder(self, project_name: str) -> Path | None:
        """
        Find a project folder by name.

        Searches both the folder name and the draft_name in meta.
        """
        if not self.drafts_folder.is_dir():
            return None

        # Direct folder name match
        direct = self.drafts_folder / project_name
        if direct.is_dir() and (direct / "draft_content.json").exists():
            return direct

        # Search by draft_name in meta
        for entry in self.drafts_folder.iterdir():
            if not entry.is_dir():
                continue
            meta_file = entry / "draft_meta_info.json"
            if meta_file.exists():
                try:
                    meta = _read_json(meta_file)
                    if meta.get("draft_name", "") == project_name:
                        return entry
                except (json.JSONDecodeError, OSError):
                    continue

        return None

    # ------------------------------------------------------------------
    # Loading & saving
    # ------------------------------------------------------------------

    def load_draft(self, project_name: str) -> DraftContent:
        """
        Load a project's draft_content.json into a DraftContent model.

        Args:
            project_name: The project name or folder name.

        Returns:
            A DraftContent Pydantic model.

        Raises:
            FileNotFoundError: If the project doesn't exist.
        """
        folder = self.get_project_folder(project_name)
        if not folder:
            raise FileNotFoundError(f"Project not found: {project_name}")

        draft_file = folder / "draft_content.json"
        data = _read_json(draft_file)
        return DraftContent.model_validate(data)

    def save_draft(self, project_name: str, draft: DraftContent, backup: bool = True) -> Path:
        """
        Save a DraftContent model back to draft_content.json.

        Args:
            project_name: The project name or folder name.
            draft: The DraftContent model to save.
            backup: If True, create a backup before overwriting.

        Returns:
            Path to the saved draft_content.json.

        Raises:
            FileNotFoundError: If the project doesn't exist.
        """
        folder = self.get_project_folder(project_name)
        if not folder:
            raise FileNotFoundError(f"Project not found: {project_name}")

        draft_file = folder / "draft_content.json"

        # Backup first
        if backup and draft_file.exists():
            self.backup_project(project_name)

        # Update modification time
        draft.update_time = _now_timestamp()

        # Serialize — use model_dump with mode="json" for clean output
        data = draft.model_dump(mode="json")
        _write_json(draft_file, data)

        # Also update meta and root_meta_info
        self._update_meta(folder, draft)
        self._update_root_meta(draft, folder)

        logger.info("Saved draft for project: %s", project_name)
        return draft_file

    def _update_meta(self, folder: Path, draft: DraftContent) -> None:
        """Update the draft_meta_info.json with current state."""
        meta_file = folder / "draft_meta_info.json"
        meta: dict[str, Any] = {}
        if meta_file.exists():
            try:
                meta = _read_json(meta_file)
            except (json.JSONDecodeError, OSError):
                pass

        meta.update({
            "draft_id": draft.id,
            "draft_name": draft.name or folder.name,
            "tm_draft_modified": _now_timestamp(),
            "draft_timeline_materials_size_": self._count_materials(draft),
        })

        _write_json(meta_file, meta)

    def _count_materials(self, draft: DraftContent) -> int:
        """Count total materials in a draft."""
        m = draft.materials
        return len(m.videos) + len(m.audios) + len(m.texts)

    def _update_root_meta(self, draft: DraftContent | None, folder: Path | None, draft_id: str | None = None, delete: bool = False) -> None:
        """Update the root_meta_info.json which CapCut uses to list projects on the home screen."""
        local_root_meta_file = self.drafts_folder / "root_meta_info.json"
        
        # Determine the real AppData path
        local_appdata = os.environ.get("LOCALAPPDATA", "")
        real_root_dir = None
        real_root_file = None
        if local_appdata:
            real_root_dir = Path(local_appdata) / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft"
            real_root_file = real_root_dir / "root_meta_info.json"
        
        root_meta = {"all_draft_store": [], "draft_ids": 0, "root_path": str(self.drafts_folder).replace("\\", "/")}
        
        # We must read from the REAL AppData file to preserve older projects, 
        # but because of the sandbox, we have to copy it to a temp file first using powershell.
        import subprocess
        
        tmp_path_obj = self.drafts_folder / ".tmp_meta_read.json"
        tmp_path = str(tmp_path_obj)
        
        if real_root_file and real_root_file.exists():
            try:
                ps_cmd = f'Copy-Item -Path "{real_root_file}" -Destination "{tmp_path}" -Force'
                subprocess.run(["powershell", "-Command", ps_cmd], check=False, creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0)
                if tmp_path_obj.exists():
                    root_meta = _read_json(tmp_path_obj)
            except Exception:
                pass
            finally:
                try:
                    tmp_path_obj.unlink(missing_ok=True)
                except OSError:
                    pass
        elif local_root_meta_file.exists():
            try:
                root_meta = _read_json(local_root_meta_file)
            except (json.JSONDecodeError, OSError):
                pass
                
        stores = root_meta.get("all_draft_store", [])
        
        d_id = draft.id if draft else draft_id
        
        # Remove existing entry if present
        stores = [s for s in stores if s.get("draft_id") != d_id]
        
        if not delete and draft and folder:
            # Add new/updated entry
            draft_fold_path = str(folder).replace("\\", "/")
            draft_json_file = str(folder / "draft_content.json").replace("/", "\\")  # CapCut mixes slashes here
            entry = {
                "draft_cover": "",
                "draft_fold_path": draft_fold_path,
                "draft_id": draft.id,
                "draft_is_ai_shorts": False,
                "draft_is_cloud_temp_draft": False,
                "draft_is_invisible": False,
                "draft_is_web_article_video": False,
                "draft_json_file": draft_json_file,
                "draft_name": draft.name or folder.name,
                "draft_new_version": "",
                "draft_root_path": str(self.drafts_folder),
                "draft_timeline_materials_size": self._count_materials(draft),
                "draft_type": "",
                "draft_web_article_video_enter_from": "",
                "streaming_edit_draft_ready": True,
                "tm_draft_cloud_completed": "",
                "tm_draft_cloud_entry_id": -1,
                "tm_draft_cloud_modified": 0,
                "tm_draft_cloud_parent_entry_id": -1,
                "tm_draft_cloud_space_id": -1,
                "tm_draft_cloud_user_id": -1,
                "tm_draft_create": draft.create_time,
                "tm_draft_modified": draft.update_time,
                "tm_draft_removed": 0,
                "tm_duration": draft.duration,
            }
            # Insert at the beginning so it shows up first
            stores.insert(0, entry)
            
        root_meta["all_draft_store"] = stores
        root_meta["draft_ids"] = len(stores)
        
        
        # We write to the local root_meta_info.json in the current drafts folder just in case
        _write_json(local_root_meta_file, root_meta)
        
        # HACK: Windows Store Python sandboxes writes to AppData/Local. 
        # CapCut ALWAYS reads the home screen index from the real AppData/Local.
        # We must forcefully push this JSON to the real AppData location using PowerShell to escape the sandbox.
        if real_root_dir and real_root_file:
            real_root_dir.mkdir(parents=True, exist_ok=True)
            
            tmp_write_obj = self.drafts_folder / ".tmp_meta_write.json"
            tmp_write_path = str(tmp_write_obj)
            
            _write_json(tmp_write_obj, root_meta)
            
            try:
                ps_cmd = f'Copy-Item -Path "{tmp_write_path}" -Destination "{real_root_file}" -Force'
                subprocess.run(
                    ["powershell", "-Command", ps_cmd], 
                    check=False, 
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
                )
            finally:
                try:
                    tmp_write_obj.unlink(missing_ok=True)
                except OSError:
                    pass

    # ------------------------------------------------------------------
    # Create & delete
    # ------------------------------------------------------------------

    def create_project(
        self,
        name: str,
        width: int = 1920,
        height: int = 1080,
        fps: float = 30.0,
        ratio: str = "16:9",
    ) -> DraftContent:
        """
        Create a new empty CapCut project.

        Args:
            name: Project name.
            width: Canvas width in pixels.
            height: Canvas height in pixels.
            fps: Frames per second.
            ratio: Aspect ratio string (e.g., "16:9").

        Returns:
            The new DraftContent model.

        Raises:
            FileExistsError: If a project with this name already exists.
        """
        # Create folder with a unique name
        folder_name = f"{_now_timestamp()}_{name.replace(' ', '_')}"
        folder = self.drafts_folder / folder_name

        if folder.exists():
            raise FileExistsError(f"Project folder already exists: {folder}")

        folder.mkdir(parents=True, exist_ok=True)

        now = _now_timestamp()

        # Build a minimal valid draft
        draft = DraftContent(
            id=_new_id(),
            name=name,
            duration=0,
            fps=fps,
            canvas_config=CanvasConfig(width=width, height=height, ratio=ratio),
            tracks=[],
            materials=Materials(
                canvases=[{
                    "album_image": "",
                    "blur": 0.0,
                    "color": "",
                    "id": _new_id(),
                    "image": "",
                    "image_id": "",
                    "image_name": "",
                    "source_platform": 0,
                    "team_id": "",
                    "type": "canvas_color",
                }],
            ),
            create_time=now,
            update_time=now,
        )

        # Write draft_content.json
        data = draft.model_dump(mode="json")
        _write_json(folder / "draft_content.json", data)

        # Write draft_meta_info.json
        meta = {
            "draft_id": draft.id,
            "draft_name": name,
            "draft_root_path": str(folder),
            "tm_draft_create": now,
            "tm_draft_modified": now,
            "draft_fold_path": str(self.drafts_folder),
            "draft_timeline_materials_size_": 0,
        }
        _write_json(folder / "draft_meta_info.json", meta)

        self._update_root_meta(draft, folder)

        logger.info("Created new project: %s at %s", name, folder)
        return draft

    def duplicate_project(self, source_name: str, new_name: str) -> DraftContent:
        """
        Duplicate an existing project.

        Args:
            source_name: Name of the project to copy.
            new_name: Name for the new project.

        Returns:
            The duplicated DraftContent model.

        Raises:
            FileNotFoundError: If the source project doesn't exist.
        """
        source_folder = self.get_project_folder(source_name)
        if not source_folder:
            raise FileNotFoundError(f"Source project not found: {source_name}")

        # Create new folder
        folder_name = f"{_now_timestamp()}_{new_name.replace(' ', '_')}"
        new_folder = self.drafts_folder / folder_name

        # Copy entire folder
        shutil.copytree(source_folder, new_folder)

        # Update the draft with new ID and name
        draft = self.load_draft(new_folder.name)
        draft.id = _new_id()
        draft.name = new_name
        draft.create_time = _now_timestamp()
        draft.update_time = _now_timestamp()

        # Save back
        data = draft.model_dump(mode="json")
        _write_json(new_folder / "draft_content.json", data)

        # Update meta and root index
        self._update_meta(new_folder, draft)
        self._update_root_meta(draft, new_folder)

        logger.info("Duplicated project '%s' -> '%s'", source_name, new_name)
        return draft

    def delete_project(self, project_name: str) -> bool:
        """
        Delete a project folder.

        Args:
            project_name: Name of the project to delete.

        Returns:
            True if deleted, False if not found.
        """
        folder = self.get_project_folder(project_name)
        if not folder:
            return False
            
        # Get draft ID before deletion to remove from root meta
        draft_id = None
        draft_file = folder / "draft_content.json"
        if draft_file.exists():
            try:
                draft_data = _read_json(draft_file)
                draft_id = draft_data.get("id")
            except (json.JSONDecodeError, OSError):
                pass

        shutil.rmtree(folder)
        
        if draft_id:
            self._update_root_meta(None, None, draft_id=draft_id, delete=True)
            
        logger.info("Deleted project: %s", project_name)
        return True

    # ------------------------------------------------------------------
    # Backup
    # ------------------------------------------------------------------

    def backup_project(self, project_name: str) -> Path | None:
        """
        Create a timestamped backup of a project's draft_content.json.

        The backup is saved as draft_content.json.backup.<timestamp> in
        the same project folder.

        Returns:
            Path to the backup file, or None if project not found.
        """
        folder = self.get_project_folder(project_name)
        if not folder:
            return None

        draft_file = folder / "draft_content.json"
        if not draft_file.exists():
            return None

        backup_name = f"draft_content.json.backup.{_now_timestamp()}"
        backup_path = folder / backup_name
        shutil.copy2(draft_file, backup_path)

        logger.info("Backed up project %s to %s", project_name, backup_name)
        return backup_path

    # ------------------------------------------------------------------
    # Track helpers
    # ------------------------------------------------------------------

    def get_or_create_track(
        self, draft: DraftContent, track_type: str, index: int = 0
    ) -> Track:
        """
        Get an existing track of the given type, or create a new one.

        Args:
            draft: The DraftContent to search.
            track_type: "video", "audio", or "text".
            index: Which track of that type (0 = first/main).

        Returns:
            The Track object.
        """
        matching = [t for t in draft.tracks if t.type == track_type]
        if len(matching) > index:
            return matching[index]

        # Create new track
        track = Track(
            id=_new_id(),
            type=track_type,
            attribute=0,
            flag=0,
            is_default_name=True,
            name="",
            segments=[],
        )
        draft.tracks.append(track)
        return track

    def recalculate_duration(self, draft: DraftContent) -> int:
        """
        Recalculate and update the total project duration.

        Scans all tracks/segments and sets draft.duration to the
        furthest endpoint.

        Returns:
            The new duration in microseconds.
        """
        max_end = 0
        for track in draft.tracks:
            for seg in track.segments:
                end = seg.target_timerange.start + seg.target_timerange.duration
                if end > max_end:
                    max_end = end

        draft.duration = max_end
        return max_end

    # ------------------------------------------------------------------
    # Material helpers
    # ------------------------------------------------------------------

    def add_video_material(
        self,
        draft: DraftContent,
        file_path: str,
        duration_us: int,
        width: int = 0,
        height: int = 0,
        is_photo: bool = False,
    ) -> VideoMaterial:
        """Add a video/image material to the draft and return it."""
        mat = VideoMaterial(
            id=_new_id(),
            path=file_path,
            type="photo" if is_photo else "video",
            width=width,
            height=height,
            duration=duration_us,
            material_name=Path(file_path).stem,
        )
        draft.materials.videos.append(mat)
        return mat

    def add_audio_material(
        self, draft: DraftContent, file_path: str, duration_us: int
    ) -> AudioMaterial:
        """Add an audio material to the draft and return it."""
        mat = AudioMaterial(
            id=_new_id(),
            path=file_path,
            duration=duration_us,
            name=Path(file_path).stem,
            material_name=Path(file_path).stem,
        )
        draft.materials.audios.append(mat)
        return mat

    def add_text_material(
        self,
        draft: DraftContent,
        text: str,
        font_size: float = 15.0,
        color: str = "#FFFFFF",
    ) -> TextMaterial:
        """Add a text material to the draft and return it."""
        content_json = json.dumps({"text": text})
        mat = TextMaterial(
            id=_new_id(),
            content=content_json,
            base_content=text,
            font_size=font_size,
            text_color=color,
            text_size=int(font_size * 2),
        )
        draft.materials.texts.append(mat)
        return mat

    def add_speed_material(self, draft: DraftContent, speed: float = 1.0) -> SpeedConfig:
        """Add a speed material and return it."""
        mat = SpeedConfig(id=_new_id(), speed=speed)
        draft.materials.speeds.append(mat)
        return mat

    def add_audio_fade_material(
        self, draft: DraftContent, fade_in: int = 0, fade_out: int = 0
    ) -> AudioFade:
        """Add an audio fade material and return it."""
        mat = AudioFade(
            id=_new_id(),
            fade_in_duration=fade_in,
            fade_out_duration=fade_out,
        )
        draft.materials.audio_fades.append(mat)
        return mat

    # ------------------------------------------------------------------
    # Segment (clip) helpers
    # ------------------------------------------------------------------

    def create_clip(
        self,
        material_id: str,
        clip_type: str,
        source_start_us: int,
        source_duration_us: int,
        target_start_us: int,
        target_duration_us: int,
        extra_material_refs: list[str] | None = None,
        volume: float = 1.0,
    ) -> Clip:
        """
        Create a new Clip (segment) linking a material to a timeline position.

        Args:
            material_id: ID of the material this clip uses.
            clip_type: "video", "audio", or "text".
            source_start_us: Start position in the source material (μs).
            source_duration_us: Duration of the source content (μs).
            target_start_us: Position on the timeline (μs).
            target_duration_us: Duration on the timeline (μs).
            extra_material_refs: Additional material IDs (speed, fade, etc.).
            volume: Volume level (0.0 to 1.0).

        Returns:
            A new Clip object.
        """
        return Clip(
            id=_new_id(),
            type=clip_type,
            material_id=material_id,
            source_timerange=TimeRange(start=source_start_us, duration=source_duration_us),
            target_timerange=TimeRange(start=target_start_us, duration=target_duration_us),
            extra_material_refs=extra_material_refs or [],
            volume=volume,
        )

    def find_segment_by_id(
        self, draft: DraftContent, segment_id: str
    ) -> tuple[Track, Clip] | None:
        """
        Find a segment by ID across all tracks.

        Returns:
            A (Track, Clip) tuple, or None if not found.
        """
        for track in draft.tracks:
            for seg in track.segments:
                if seg.id == segment_id:
                    return (track, seg)
        return None

    def get_track_end_position(self, track: Track) -> int:
        """Get the end position (μs) of the last segment on a track."""
        if not track.segments:
            return 0
        return max(
            seg.target_timerange.start + seg.target_timerange.duration
            for seg in track.segments
        )
