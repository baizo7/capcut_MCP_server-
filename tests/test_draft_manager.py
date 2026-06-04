"""
Tests for the DraftManager and model parsing.

Uses a temporary directory to simulate the CapCut drafts folder
so tests don't modify real projects.
"""

import json
import shutil
import tempfile
from pathlib import Path

import pytest

from capcut_mcp.config import ms_to_us, us_to_ms, us_to_seconds
from capcut_mcp.draft_manager import DraftManager
from capcut_mcp.models import DraftContent

# Path to the sample fixture
FIXTURE_DIR = Path(__file__).parent / "fixtures"
SAMPLE_DRAFT = FIXTURE_DIR / "sample_draft.json"


@pytest.fixture
def tmp_drafts(tmp_path):
    """Create a temporary drafts folder with a sample project."""
    drafts_folder = tmp_path / "drafts"
    drafts_folder.mkdir()

    # Create a sample project folder
    project_folder = drafts_folder / "sample_project"
    project_folder.mkdir()

    # Copy the sample draft
    shutil.copy(SAMPLE_DRAFT, project_folder / "draft_content.json")

    # Create a meta file
    meta = {
        "draft_id": "TEST-0000-0000-0000-000000000001",
        "draft_name": "Test Project",
        "draft_root_path": str(project_folder),
        "tm_draft_create": 1700000000,
        "tm_draft_modified": 1700000000,
    }
    with open(project_folder / "draft_meta_info.json", "w") as f:
        json.dump(meta, f)

    return drafts_folder


@pytest.fixture
def manager(tmp_drafts):
    """Create a DraftManager using the temp drafts folder."""
    return DraftManager(tmp_drafts)


# -----------------------------------------------------------------------
# Model tests
# -----------------------------------------------------------------------

class TestModels:
    """Test Pydantic model parsing."""

    def test_parse_sample_draft(self):
        """Verify the sample draft fixture can be parsed into a DraftContent model."""
        data = json.loads(SAMPLE_DRAFT.read_text())
        draft = DraftContent.model_validate(data)

        assert draft.id == "TEST-0000-0000-0000-000000000001"
        assert draft.name == "Test Project"
        assert draft.fps == 30.0
        assert draft.canvas_config.width == 1920
        assert draft.canvas_config.height == 1080
        assert draft.canvas_config.ratio == "16:9"

    def test_draft_has_tracks(self):
        """Verify tracks and segments are correctly parsed."""
        data = json.loads(SAMPLE_DRAFT.read_text())
        draft = DraftContent.model_validate(data)

        assert len(draft.tracks) == 1
        assert draft.tracks[0].type == "video"
        assert len(draft.tracks[0].segments) == 1

        seg = draft.tracks[0].segments[0]
        assert seg.id == "SEG-VIDEO-0001"
        assert seg.material_id == "MAT-VIDEO-0001"
        assert seg.source_timerange.duration == 10_000_000  # 10 seconds in μs

    def test_draft_has_materials(self):
        """Verify materials are correctly parsed."""
        data = json.loads(SAMPLE_DRAFT.read_text())
        draft = DraftContent.model_validate(data)

        assert len(draft.materials.videos) == 1
        assert draft.materials.videos[0].id == "MAT-VIDEO-0001"
        assert draft.materials.videos[0].path == "C:\\test\\sample_video.mp4"

    def test_roundtrip_serialization(self):
        """Verify model can be serialized and re-parsed without data loss."""
        data = json.loads(SAMPLE_DRAFT.read_text())
        draft = DraftContent.model_validate(data)

        # Serialize back
        exported = draft.model_dump(mode="json")

        # Re-parse
        draft2 = DraftContent.model_validate(exported)
        assert draft2.id == draft.id
        assert draft2.name == draft.name
        assert len(draft2.tracks) == len(draft.tracks)
        assert len(draft2.materials.videos) == len(draft.materials.videos)


# -----------------------------------------------------------------------
# DraftManager tests
# -----------------------------------------------------------------------

class TestDraftManager:
    """Test DraftManager operations."""

    def test_list_projects(self, manager):
        """Test listing projects."""
        projects = manager.list_projects()
        assert len(projects) == 1
        assert projects[0]["name"] == "Test Project"
        assert projects[0]["folder_name"] == "sample_project"

    def test_load_draft(self, manager):
        """Test loading a project."""
        draft = manager.load_draft("sample_project")
        assert draft.name == "Test Project"
        assert draft.fps == 30.0

    def test_load_draft_by_name(self, manager):
        """Test loading a project by its draft_name (from meta)."""
        draft = manager.load_draft("Test Project")
        assert draft.name == "Test Project"

    def test_load_missing_project(self, manager):
        """Test loading a non-existent project raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            manager.load_draft("nonexistent")

    def test_create_project(self, manager):
        """Test creating a new project."""
        draft = manager.create_project(
            name="New Project",
            width=1080,
            height=1920,
            fps=60.0,
            ratio="9:16",
        )
        assert draft.name == "New Project"
        assert draft.canvas_config.width == 1080
        assert draft.canvas_config.height == 1920
        assert draft.fps == 60.0

        # Verify it appears in the project list
        projects = manager.list_projects()
        names = [p["name"] for p in projects]
        assert "New Project" in names

    def test_save_draft(self, manager):
        """Test saving a modified draft."""
        draft = manager.load_draft("sample_project")
        draft.name = "Modified Project"
        manager.save_draft("sample_project", draft)

        # Reload and verify
        reloaded = manager.load_draft("sample_project")
        assert reloaded.name == "Modified Project"

    def test_backup_project(self, manager, tmp_drafts):
        """Test that backup creates a timestamped copy."""
        backup_path = manager.backup_project("sample_project")
        assert backup_path is not None
        assert backup_path.exists()
        assert "draft_content.json.backup" in backup_path.name

    def test_duplicate_project(self, manager):
        """Test duplicating a project."""
        draft = manager.duplicate_project("sample_project", "Copy of Test")
        assert draft.name == "Copy of Test"
        assert draft.id != "TEST-0000-0000-0000-000000000001"  # New ID

        projects = manager.list_projects()
        assert len(projects) == 2

    def test_delete_project(self, manager):
        """Test deleting a project."""
        result = manager.delete_project("sample_project")
        assert result is True

        projects = manager.list_projects()
        assert len(projects) == 0

    def test_delete_missing_project(self, manager):
        """Test deleting a non-existent project returns False."""
        result = manager.delete_project("nonexistent")
        assert result is False


# -----------------------------------------------------------------------
# Track and material helper tests
# -----------------------------------------------------------------------

class TestTrackHelpers:
    """Test track and material manipulation helpers."""

    def test_get_or_create_track(self, manager):
        """Test creating a new track type."""
        draft = manager.load_draft("sample_project")

        # Should find existing video track
        video_track = manager.get_or_create_track(draft, "video")
        assert video_track.type == "video"
        assert len(draft.tracks) == 1  # no new track added

        # Should create a new audio track
        audio_track = manager.get_or_create_track(draft, "audio")
        assert audio_track.type == "audio"
        assert len(draft.tracks) == 2

    def test_add_video_material(self, manager):
        """Test adding a video material."""
        draft = manager.load_draft("sample_project")
        mat = manager.add_video_material(
            draft, "C:\\test\\another.mp4", 5_000_000
        )
        assert mat.path == "C:\\test\\another.mp4"
        assert mat.duration == 5_000_000
        assert len(draft.materials.videos) == 2

    def test_add_text_material(self, manager):
        """Test adding a text material."""
        draft = manager.load_draft("sample_project")
        mat = manager.add_text_material(draft, "Hello World", 20.0, "#FF0000")
        assert mat.base_content == "Hello World"
        assert mat.text_color == "#FF0000"
        assert len(draft.materials.texts) == 1

    def test_create_clip(self, manager):
        """Test creating a clip."""
        clip = manager.create_clip(
            material_id="MAT-001",
            clip_type="video",
            source_start_us=0,
            source_duration_us=5_000_000,
            target_start_us=0,
            target_duration_us=5_000_000,
        )
        assert clip.material_id == "MAT-001"
        assert clip.type == "video"
        assert clip.target_timerange.duration == 5_000_000

    def test_recalculate_duration(self, manager):
        """Test duration recalculation."""
        draft = manager.load_draft("sample_project")
        # Add a second clip at 10s lasting 5s
        track = draft.tracks[0]
        clip = manager.create_clip(
            material_id="MAT-VIDEO-0001",
            clip_type="video",
            source_start_us=0,
            source_duration_us=5_000_000,
            target_start_us=10_000_000,
            target_duration_us=5_000_000,
        )
        track.segments.append(clip)

        new_dur = manager.recalculate_duration(draft)
        assert new_dur == 15_000_000  # 15 seconds

    def test_find_segment_by_id(self, manager):
        """Test finding a segment by its ID."""
        draft = manager.load_draft("sample_project")
        result = manager.find_segment_by_id(draft, "SEG-VIDEO-0001")
        assert result is not None
        track, seg = result
        assert seg.id == "SEG-VIDEO-0001"
        assert track.type == "video"

    def test_find_missing_segment(self, manager):
        """Test searching for a non-existent segment returns None."""
        draft = manager.load_draft("sample_project")
        result = manager.find_segment_by_id(draft, "NONEXISTENT")
        assert result is None


# -----------------------------------------------------------------------
# Config / utility tests
# -----------------------------------------------------------------------

class TestConfig:
    """Test configuration utilities."""

    def test_ms_to_us(self):
        assert ms_to_us(1000) == 1_000_000
        assert ms_to_us(500) == 500_000
        assert ms_to_us(0) == 0

    def test_us_to_ms(self):
        assert us_to_ms(1_000_000) == 1000.0
        assert us_to_ms(500_000) == 500.0

    def test_us_to_seconds(self):
        assert us_to_seconds(1_000_000) == 1.0
        assert us_to_seconds(10_000_000) == 10.0
