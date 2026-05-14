"""
DEEPSHIP Lane conformance tests — end-to-end lifecycle in temp git repos.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure DEEPSHIP is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from adapters.lane import LaneManager, LanesRegistry


def _init_temp_repo() -> Path:
    """Create a temp git repo with a dummy file. Returns the repo path."""
    d = Path(tempfile.mkdtemp())
    subprocess.run(["git", "-C", str(d), "init"], capture_output=True, check=True)
    subprocess.run(["git", "-C", str(d), "config", "user.name", "Test"], capture_output=True)
    subprocess.run(["git", "-C", str(d), "config", "user.email", "test@test"], capture_output=True)
    (d / "README.md").write_text("# Test Repo\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(d), "add", "README.md"], capture_output=True)
    subprocess.run(["git", "-C", str(d), "commit", "-m", "initial"], capture_output=True)
    return d


class TestLanesRegistry:
    def test_add_and_list(self):
        d = tempfile.mkdtemp()
        r = LanesRegistry(d)
        r.add({"name": "lane-a", "branch": "d/lane-a", "worktree_path": "/t/a",
               "base_branch": "main"})
        r.add({"name": "lane-b", "branch": "d/lane-b", "worktree_path": "/t/b",
               "base_branch": "main"})
        lanes = r.list_all()
        assert len(lanes) == 2
        assert lanes[0]["name"] in ("lane-a", "lane-b")

    def test_duplicate_rejected(self):
        d = tempfile.mkdtemp()
        r = LanesRegistry(d)
        r.add({"name": "x", "branch": "d/x", "worktree_path": "/t/x",
               "base_branch": "main"})
        result = r.add({"name": "x", "branch": "d/x2", "worktree_path": "/t/x2",
                        "base_branch": "main"})
        assert not result["success"]

    def test_remove(self):
        d = tempfile.mkdtemp()
        r = LanesRegistry(d)
        r.add({"name": "x", "branch": "d/x", "worktree_path": "/t/x",
               "base_branch": "main"})
        r.remove("x")
        assert len(r.list_all()) == 0

    def test_update_status(self):
        d = tempfile.mkdtemp()
        r = LanesRegistry(d)
        r.add({"name": "x", "branch": "d/x", "worktree_path": "/t/x",
               "base_branch": "main"})
        r.update("x", status="merged")
        assert r.get("x")["status"] == "merged"

    def test_get_missing(self):
        d = tempfile.mkdtemp()
        r = LanesRegistry(d)
        assert r.get("nonexistent") is None


class TestLaneCreateRemove:
    def test_create_initializes_lane(self):
        repo = _init_temp_repo()
        mgr = LaneManager(repo)
        result = mgr.create("test-lane")
        assert result["success"], f"Create failed: {result.get('error')}"
        lane_path = Path(result["path"])
        assert lane_path.exists()
        assert lane_path == repo / ".deepship" / "lanes" / "test-lane"
        assert not (repo.parent / f"{repo.name}-lanes").exists()
        # lane metadata lives inside the lane worktree's own .deepship/.
        lane_home = lane_path / ".deepship"
        assert (lane_home / "lane.json").exists()
        assert (lane_home / "state.json").exists()
        assert (lane_home / "work_units.json").exists()
        assert (lane_home / "handoff.md").exists()
        assert (lane_path / "Prompt.md").exists()
        # Registry should have entry
        lanes = mgr.registry.list_all()
        assert any(l["name"] == "test-lane" for l in lanes)

        shutil.rmtree(repo, ignore_errors=True)

    def test_create_and_remove_clean(self):
        repo = _init_temp_repo()
        mgr = LaneManager(repo)
        mgr.create("test-lane")
        result = mgr.remove("test-lane", discard=True)
        assert result["success"], f"Remove failed: {result.get('error')}"
        # Registry should be clean
        assert len(mgr.registry.list_all()) == 0
        # Lane worktree and metadata should be gone.
        assert not Path(result["path"]).exists()
        assert not (repo / ".deepship" / "lanes" / "test-lane").exists()

        shutil.rmtree(repo, ignore_errors=True)

    def test_remove_refuses_dirty_lane(self):
        repo = _init_temp_repo()
        mgr = LaneManager(repo)
        mgr.create("test-lane")
        # Make a change
        lane_path = Path(mgr.list()[0]["path"])
        (lane_path / "new_file.txt").write_text("dirty", encoding="utf-8")
        # Remove without discard should fail
        result = mgr.remove("test-lane", discard=False)
        assert not result["success"]
        assert "live work" in result["error"].lower() or "uncommitted" in result["error"].lower()
        # Remove with discard should succeed
        result = mgr.remove("test-lane", discard=True)
        assert result["success"]

        shutil.rmtree(repo, ignore_errors=True)

    def test_two_lanes_are_isolated(self):
        repo = _init_temp_repo()
        mgr = LaneManager(repo)
        mgr.create("lane-a")
        mgr.create("lane-b")
        lanes = mgr.list()
        assert len(lanes) == 2

        # Verify two lanes have independent worktree-local .deepship metadata.
        for l in lanes:
            lane_home = Path(l["lane_home"])
            state_path = lane_home / "state.json"
            assert state_path.exists()
            state = json.loads(state_path.read_text(encoding="utf-8"))
            assert state["current_state"] == "READ_CONTEXT"
            assert (lane_home / "handoff.md").exists()
            assert Path(l["path"]) / ".deepship" == lane_home

        # Both in registry
        assert len(mgr.registry.list_all()) == 2

        # Clean up
        for name in ["lane-a", "lane-b"]:
            mgr.remove(name, discard=True)
        assert len(mgr.registry.list_all()) == 0

        shutil.rmtree(repo, ignore_errors=True)


class TestLaneMerge:
    def test_merge_dry_run_shows_diff(self):
        repo = _init_temp_repo()
        mgr = LaneManager(repo)
        mgr.create("merge-test")
        lane_path = Path(mgr.list()[0]["path"])

        # Add a real change
        (lane_path / "new_code.py").write_text("# new feature\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(lane_path), "add", "new_code.py"], capture_output=True)
        subprocess.run(["git", "-C", str(lane_path), "commit", "-m", "feat: new code"], capture_output=True)

        # Dry run
        result = mgr.merge("merge-test", apply=False)
        assert result["success"], f"Merge dry-run failed: {result.get('error')}"
        assert result.get("dry_run")
        assert "new_code.py" in result.get("diff_preview", "")

        # Clean up
        mgr.remove("merge-test", discard=True)
        shutil.rmtree(repo, ignore_errors=True)

    def test_merge_rejects_force_added_deepship_metadata(self):
        repo = _init_temp_repo()
        mgr = LaneManager(repo)
        mgr.create("bad-lane")
        lane_path = Path(mgr.list()[0]["path"])

        # Re-add a .deepship/ file (simulating bad behavior that bypasses .gitignore)
        (lane_path / ".deepship" / "bad_meta.json").write_text("{}", encoding="utf-8")
        subprocess.run(["git", "-C", str(lane_path), "add", "-f", ".deepship/bad_meta.json"],
                       capture_output=True)
        subprocess.run(["git", "-C", str(lane_path), "commit", "-m", "oops: re-added meta"],
                       capture_output=True)

        # Merge should refuse
        result = mgr.merge("bad-lane", apply=False)
        assert not result["success"]
        assert ".deepship" in result.get("error", "")

        mgr.remove("bad-lane", discard=True)
        shutil.rmtree(repo, ignore_errors=True)

    def test_merge_refuses_if_wus_not_integrated(self):
        repo = _init_temp_repo()
        mgr = LaneManager(repo)
        mgr.create("wip-lane")
        lane_path = Path(mgr.list()[0]["path"])

        # Add a pending WU
        wu_path = repo / ".deepship" / "lanes" / "wip-lane" / ".deepship" / "work_units.json"
        wus = json.loads(wu_path.read_text(encoding="utf-8"))
        wus["work_units"].append({
            "id": "WU-001", "status": "in_progress",
            "goal": "test", "files_allowed": ["a.py"],
            "owner": "orchestrator"
        })
        json.dump(wus, open(str(wu_path), "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        subprocess.run(["git", "-C", str(lane_path), "add", "-A"], capture_output=True)
        subprocess.run(["git", "-C", str(lane_path), "commit", "-m", "wip WU"], capture_output=True)

        # Merge should refuse (WU not integrated)
        result = mgr.merge("wip-lane", apply=False)
        assert not result["success"]
        assert "WU" in result.get("error", "")

        mgr.remove("wip-lane", discard=True)
        shutil.rmtree(repo, ignore_errors=True)


class TestLaneFinalize:
    def test_finalize_dry_run_does_not_cleanup(self):
        repo = _init_temp_repo()
        mgr = LaneManager(repo)
        mgr.create("finalize-dry")
        lane_path = Path(mgr.list()[0]["path"])

        (lane_path / "feature.py").write_text("# feature\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(lane_path), "add", "feature.py"], capture_output=True)
        subprocess.run(["git", "-C", str(lane_path), "commit", "-m", "feat: feature"], capture_output=True)

        result = mgr.finalize("finalize-dry", apply=False)

        assert result["success"], result.get("error")
        assert result["dry_run"]
        assert Path(result["path"]).exists()
        assert Path(result["lane_home"]).exists()
        assert "feature.py" in result.get("diff_preview", "")

        mgr.remove("finalize-dry", discard=True)
        shutil.rmtree(repo, ignore_errors=True)

    def test_finalize_apply_merges_archives_and_removes_lane(self):
        repo = _init_temp_repo()
        mgr = LaneManager(repo)
        mgr.create("finalize-apply")
        lane = mgr.list()[0]
        lane_path = Path(lane["path"])
        lane_home = Path(lane["lane_home"])

        (lane_path / "feature.py").write_text("# feature\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(lane_path), "add", "feature.py"], capture_output=True)
        subprocess.run(["git", "-C", str(lane_path), "commit", "-m", "feat: feature"], capture_output=True)

        result = mgr.finalize("finalize-apply", apply=True)

        assert result["success"], result.get("error")
        assert not result["dry_run"]
        assert (repo / "feature.py").exists()
        assert not lane_home.exists()
        assert not lane_path.exists()
        assert mgr.registry.get("finalize-apply") is None
        archive_root = repo / ".deepship" / "lanes-archive"
        archives = list(archive_root.glob("finalize-apply-*"))
        assert archives
        assert (archives[0] / "lane.json").exists()
        assert not (archives[0] / ".git").exists()

        shutil.rmtree(repo, ignore_errors=True)
