"""
DEEPSHIP v0 self-verification.
Zero external dependencies. Run from repo root:
  python checks/verify.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
errors = []
warnings = []

def err(msg):
    errors.append(msg)
    print(f"  FAIL: {msg}")

def warn(msg):
    warnings.append(msg)
    print(f"  WARN: {msg}")

def ok(msg):
    print(f"  OK: {msg}")


def check_core_code():
    """Essential Python modules must exist."""
    print("\n[1] Core code integrity")
    required = [
        ("adapters/__init__.py", "top-level adapter package"),
        ("adapters/brain/__init__.py", "Brain package"),
        ("adapters/brain/dispatch.py", "WU dispatcher"),
        ("adapters/brain/monitor.py", "Lane monitor"),
        ("adapters/parallel/__init__.py", "Parallel package"),
        ("adapters/parallel/spawn_lane.py", "Lane spawner"),
        ("adapters/parallel/_utils.py", "Shared utilities"),
        ("adapters/gates.py", "Hard gates (boundary, land, schema)"),
    ]
    for path, desc in required:
        if (ROOT / path).exists():
            ok(f"{path} ({desc})")
        else:
            err(f"{path} NOT FOUND ({desc})")


def check_lane_index():
    """If lanes/index.json exists, validate its structure."""
    print("\n[2] Lane index integrity")
    idx = ROOT / ".deepship" / "lanes" / "index.json"
    if not idx.exists():
        ok("no lanes/index.json — nothing to check")
        return

    try:
        data = json.loads(idx.read_text(encoding="utf-8"))
    except Exception as e:
        err(f"lanes/index.json invalid JSON: {e}")
        return

    if not isinstance(data, dict):
        err("lanes/index.json must be a JSON object")
        return

    for lane_id, info in data.items():
        required = ["status", "task", "worktree", "files_claimed", "spawned_at"]
        missing = [k for k in required if k not in info]
        if missing:
            err(f"{lane_id}: missing fields {missing}")
        else:
            ok(f"{lane_id}: status={info['status']}")


def check_scope():
    """If scope.md exists, verify it has required sections (current Chinese template)."""
    print("\n[3] Scope integrity")
    scope = ROOT / ".deepship" / "scope.md"
    if not scope.exists():
        warn("no scope.md — run /deepship-scope before spawning")
        return

    text = scope.read_text(encoding="utf-8")
    # 当前 deepship-scope 中文模板的必需段
    required_sections = [
        "已确认事实", "推断判断", "未知问题",
        "可能失败点", "拟拆分 Work Units", "建议",
    ]
    for section in required_sections:
        if section in text:
            ok(f"scope.md: '{section}' present")
        else:
            warn(f"scope.md: '{section}' MISSING")

    # machine-readable recommendation 字段
    from adapters.gates import parse_recommendation
    rec = parse_recommendation(text)
    if rec in ("spawn", "do_not_spawn"):
        ok(f"scope.md: recommendation={rec}")
    elif rec is not None:
        warn(f"scope.md: recommendation='{rec}' (unrecognized)")
    else:
        warn("scope.md: recommendation field MISSING or malformed")


def check_land_report():
    """If land-report.md exists, verify it has boundary/evidence/integration."""
    print("\n[4] Land report integrity")
    lr = ROOT / ".deepship" / "land-report.md"
    if not lr.exists():
        ok("no land-report.md — nothing to check")
        return

    text = lr.read_text(encoding="utf-8")
    for check_name in ["Boundary", "Evidence", "Integration"]:
        if check_name in text:
            ok(f"land-report.md: '{check_name}' check present")
        else:
            warn(f"land-report.md: '{check_name}' check MISSING")


def check_contracts():
    """Verify core contracts: imports work, signatures match, paths consistent."""
    print("\n[5] Contract verification")

    # 5a: All core imports must succeed
    try:
        from adapters.brain import BrainDispatcher, BrainMonitor  # noqa: F811
        ok("import BrainDispatcher, BrainMonitor")
    except Exception as e:
        err(f"Brain import failed: {e}")

    try:
        from adapters.parallel.spawn_lane import LaneSpawner, list_active_lanes
        ok("import LaneSpawner, list_active_lanes")
    except Exception as e:
        err(f"spawn_lane import failed: {e}")

    # 5b: create_worktree signature must accept project_root
    try:
        from adapters.parallel._utils import create_worktree
        import inspect
        sig = inspect.signature(create_worktree)
        params = list(sig.parameters.keys())
        if "project_root" in params:
            ok(f"create_worktree signature: {params}")
        else:
            err(f"create_worktree missing project_root param: {params}")
    except Exception as e:
        err(f"create_worktree check failed: {e}")

    # 5c: Monitor._read_lane_report must read from worktree path
    try:
        import inspect
        from adapters.brain.monitor import BrainMonitor as BM
        src = inspect.getsource(BM._read_lane_report)
        if 'worktree' in src and '.deepship' in src and 'report.json' in src:
            ok("Monitor reads report from worktree path")
        else:
            err("Monitor._read_lane_report may not use worktree path")
    except Exception as e:
        warn(f"Monitor source check failed (non-critical): {e}")

    # 5d: CLI entry point — spawn_lane.py --help works
    try:
        import subprocess
        r = subprocess.run(
            [sys.executable, str(ROOT / "adapters" / "parallel" / "spawn_lane.py"), "--help"],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode == 0 and "usage:" in r.stdout:
            ok("spawn_lane.py --help works")
        else:
            err(f"spawn_lane.py --help failed: {r.stderr[:100]}")
    except Exception as e:
        err(f"spawn_lane.py --help error: {e}")

    # 5e: spawn_lane.py --list works (no crash)
    try:
        import subprocess
        r = subprocess.run(
            [sys.executable, str(ROOT / "adapters" / "parallel" / "spawn_lane.py"), "--list"],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode == 0:
            ok("spawn_lane.py --list works")
        else:
            err(f"spawn_lane.py --list failed: {r.stderr[:100]}")
    except Exception as e:
        err(f"spawn_lane.py --list error: {e}")

    # 5f: Gate contracts — boundary, land determination, schema, recommendation
    try:
        from adapters.gates import (
            validate_lane_index_entry,
            parse_recommendation,
            check_boundary,
            determine_land_status,
        )
        # Lane index schema
        assert validate_lane_index_entry({}) == ["status", "task", "worktree", "files_claimed", "spawned_at"]
        ok("gate: lane index schema contract")
        # Recommendation parsing
        assert parse_recommendation("recommendation: spawn") == "spawn"
        assert parse_recommendation("recommendation: do_not_spawn") == "do_not_spawn"
        assert parse_recommendation("recommendation: do not spawn") is None
        ok("gate: recommendation parse contract")
        # Boundary check
        r = check_boundary(["src/a.py", "utils/b.py"], ["src/"])
        assert r["pass"] is False
        assert "utils/b.py" in r["out_of_bounds"]
        ok("gate: boundary check contract")
        # Land determination
        assert determine_land_status([]) == "NOTHING TO LAND"
        ok("gate: land determination contract")
    except Exception as e:
        err(f"Gate contract verification failed: {e}")


if __name__ == "__main__":
    print(f"DEEPSHIP v0 verify — {ROOT}")
    check_core_code()
    check_lane_index()
    check_scope()
    check_land_report()
    check_contracts()
    print(f"\n{'='*40}")
    print(f"Errors: {len(errors)} | Warnings: {len(warnings)}")
    for e in errors:
        print(f"  FAIL: {e}")
    for w in warnings:
        print(f"  WARN: {w}")
    sys.exit(1 if errors else 0)
