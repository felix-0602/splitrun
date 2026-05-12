# DEEPSHIP Conformance Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn DEEPSHIP's protocol, schemas, conformance cases, and Claude Code adapter into a single testable conformance surface that can be verified before release.

**Architecture:** Extract the policy logic currently embedded in `adapters/cc/hooks/deepship_gate.py` into a reusable Python conformance package under `src/deepship/`. The hook becomes a thin adapter over the shared policy engine, while tests execute the same engine against `tests/conformance/*.json`.

**Tech Stack:** Python 3.12 standard library, `unittest`, JSON Schema-compatible fixtures, existing Markdown protocol docs.
---
## Current Reality

`core/manifest.md` declares DEEPSHIP as protocol specification, `protocol/` is authoritative, `schemas/` and `tests/conformance/` define expected behavior, and `checks/verify.py` validates structure. The missing piece is runnable semantic conformance: `adapters/cc/hooks/deepship_gate.py` currently duplicates policy logic inline, so hook behavior can drift from protocol cases.

## File Structure

- Create: `src/deepship/__init__.py`, `src/deepship/policy.py`, `src/deepship/transition.py`, `src/deepship/persistence.py`.
- Create: `tests/conformance/test_policy_cases.py`, `test_transition_cases.py`, `test_work_unit_cases.py`, `test_persistence_cases.py`.
- Modify: `adapters/cc/hooks/deepship_gate.py`, `checks/verify.py`, `adapters/claude-code/README.md`, `adapters/mate/README.md`.
---
### Task 1: Create Shared Policy Engine

**Files:**
- Create: `src/deepship/__init__.py`
- Create: `src/deepship/policy.py`
- Test: `tests/conformance/test_policy_cases.py`

- [ ] **Step 1: Write the failing policy conformance test**

Create `tests/conformance/test_policy_cases.py`:

```python
import json
import unittest
from pathlib import Path

from src.deepship.policy import evaluate_policy


ROOT = Path(__file__).resolve().parents[2]


class PolicyConformanceTest(unittest.TestCase):
    def test_policy_cases(self):
        cases = json.loads(
            (ROOT / "tests" / "conformance" / "policy_cases.json").read_text(encoding="utf-8")
        )["cases"]

        for case in cases:
            with self.subTest(case=case["name"]):
                result = evaluate_policy(
                    tool=case["tool"],
                    args=case.get("args", {}),
                    state={"current_state": case["state"]},
                    work_unit=case.get("work_unit"),
                    workspace=case.get("workspace"),
                )
                self.assertEqual(case["expected"], result.decision, result.reason)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest tests.conformance.test_policy_cases -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'src.deepship'`.

- [ ] **Step 3: Create package entry point**

Create `src/deepship/__init__.py`:

```python
"""DEEPSHIP runtime-independent conformance helpers."""

__version__ = "0.1.0"
```

- [ ] **Step 4: Implement shared policy engine**

Create `src/deepship/policy.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


READ_TOOLS = {"read_file", "grep", "glob", "git_status", "git_diff", "git_log", "Read", "Grep", "Glob"}
STATE_WRITE_TOOLS = {"write_state", "append_log"}
DOC_WRITE_TOOLS = {"write_doc"}
CODE_WRITE_TOOLS = {"write_file", "edit_file", "Write", "Edit", "MultiEdit"}
EXEC_TOOLS = {"bash", "Bash"}
TRANSITION_TOOLS = {"transition_state", "TransitionState"}

MUTATING_TOOLS = STATE_WRITE_TOOLS | DOC_WRITE_TOOLS | CODE_WRITE_TOOLS | EXEC_TOOLS
EXECUTE_STATES = {"EXECUTE", "REPAIR"}
DOC_SUFFIXES = (".md",)
DOC_PATH_PARTS = ("Documentation.md", "CHANGELOG.md", "README.md", ".deepship", "decisions", "approvals")


@dataclass(frozen=True)
class PolicyResult:
    decision: str
    reason: str

    @property
    def allowed(self) -> bool:
        return self.decision == "ALLOW"


def _allow(reason: str) -> PolicyResult:
    return PolicyResult("ALLOW", reason)


def _block(reason: str) -> PolicyResult:
    return PolicyResult("BLOCK", reason)


def _path_arg(args: dict[str, Any]) -> str:
    return str(args.get("file_path") or args.get("path") or "")


def _is_doc_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return normalized.endswith(DOC_SUFFIXES) or any(part in normalized for part in DOC_PATH_PARTS)


def _is_under_workspace(path: str, workspace: str | None) -> bool:
    if not workspace or not path:
        return True
    try:
        candidate = Path(path).resolve()
        root = Path(workspace).resolve()
        return candidate == root or root in candidate.parents
    except OSError:
        return False


def _matches_allowed(path: str, allowed: list[str]) -> bool:
    normalized = path.replace("\\", "/")
    for item in allowed:
        rule = item.replace("\\", "/").rstrip("/")
        if rule.endswith("/*"):
            prefix = rule[:-2].rstrip("/") + "/"
            if normalized.startswith(prefix):
                return True
        if normalized == rule or normalized.startswith(rule.rstrip("/") + "/"):
            return True
    return False


def evaluate_policy(
    tool: str,
    args: dict[str, Any],
    state: dict[str, Any],
    work_unit: dict[str, Any] | None = None,
    workspace: str | None = None,
) -> PolicyResult:
    current_state = str(state.get("current_state") or "READ_CONTEXT")
    file_path = _path_arg(args)

    if current_state == "COMPLETE":
        return _block("COMPLETE is terminal")

    if tool in READ_TOOLS:
        return _allow("read-only tool")

    if tool in TRANSITION_TOOLS:
        target = str(args.get("target") or args.get("to") or "")
        if target == "COMPLETE" and current_state not in {"ADVANCE", "RECORD"}:
            return _block(f"cannot transition from {current_state} to COMPLETE")
        if target == "ADVANCE" and current_state != "RECORD":
            return _block(f"cannot transition from {current_state} to ADVANCE")
        return _allow("transition allowed by policy gate")

    if tool not in MUTATING_TOOLS:
        return _allow("unknown non-mutating tool")

    if not _is_under_workspace(file_path, workspace):
        return _block(f"{file_path} is outside workspace")

    if current_state == "RECORD":
        if tool in STATE_WRITE_TOOLS:
            return _allow("RECORD can write persistent state")
        if tool in DOC_WRITE_TOOLS or (tool in CODE_WRITE_TOOLS and _is_doc_path(file_path)):
            return _allow("RECORD can write documentation")
        return _block("RECORD cannot mutate code or execute commands")

    if current_state in {"READ_CONTEXT", "MAP_REALITY", "SELECT_MILESTONE", "PLAN_STEP", "VALIDATE", "BLOCK"}:
        if current_state == "VALIDATE" and tool in EXEC_TOOLS:
            return _allow("VALIDATE can run verification commands")
        if current_state == "READ_CONTEXT" and tool in EXEC_TOOLS and str(args.get("command", "")).strip().startswith("git status"):
            return _allow("READ_CONTEXT can run git status")
        return _block(f"{current_state} does not allow {tool}")

    if current_state == "CLARIFY_INTENT":
        if tool in DOC_WRITE_TOOLS or (tool in CODE_WRITE_TOOLS and _is_doc_path(file_path)):
            return _allow("CLARIFY_INTENT can write planning docs")
        return _block("CLARIFY_INTENT cannot mutate code or execute commands")

    if current_state in EXECUTE_STATES:
        if tool in CODE_WRITE_TOOLS:
            if not work_unit:
                return _block("code write requires current work unit")
            allowed = list(work_unit.get("files_allowed") or [])
            if not allowed:
                return _block("work unit files_allowed is empty")
            if not _matches_allowed(file_path, allowed):
                return _block(f"{file_path} is outside files_allowed")
        return _allow(f"{current_state} allows {tool}")

    if current_state == "ADVANCE":
        if tool in STATE_WRITE_TOOLS or tool in DOC_WRITE_TOOLS:
            return _allow("ADVANCE can update state or delivery summary")
        return _block("ADVANCE cannot mutate code")

    return _block(f"{current_state} does not allow {tool}")
```

- [ ] **Step 5: Run test to verify it passes**

Run:

```powershell
python -m unittest tests.conformance.test_policy_cases -v
```

Expected: PASS for every case in `policy_cases.json`.

- [ ] **Step 6: Commit**

```powershell
git add src/deepship/__init__.py src/deepship/policy.py tests/conformance/test_policy_cases.py
git commit -m "test: add runnable policy conformance harness"
```

---

### Task 2: Replace Claude Code Hook Policy Duplication

**Files:**
- Modify: `adapters/cc/hooks/deepship_gate.py`
- Test: `tests/conformance/test_policy_cases.py`

- [ ] **Step 1: Add a hook regression test for CLI tool names**

Append to `tests/conformance/test_policy_cases.py`:

```python
    def test_claude_code_tool_aliases_match_policy(self):
        result = evaluate_policy(
            tool="Edit",
            args={"file_path": "src/app.py"},
            state={"current_state": "EXECUTE"},
            work_unit={"files_allowed": ["src/app.py"]},
        )
        self.assertEqual("ALLOW", result.decision)

        result = evaluate_policy(
            tool="Edit",
            args={"file_path": "src/other.py"},
            state={"current_state": "EXECUTE"},
            work_unit={"files_allowed": ["src/app.py"]},
        )
        self.assertEqual("BLOCK", result.decision)
```

- [ ] **Step 2: Run test to verify existing package supports aliases**

Run:

```powershell
python -m unittest tests.conformance.test_policy_cases -v
```

Expected: PASS.

- [ ] **Step 3: Refactor hook to call shared engine**

Modify `adapters/cc/hooks/deepship_gate.py` so the policy section imports the shared engine:

```python
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.deepship.policy import evaluate_policy
```

Replace the current `evaluate(...)` function body with:

```python
def evaluate(tool_name: str, args: dict, state: dict, wu: dict | None) -> tuple[bool, str]:
    workspace = None
    for root_candidate in [Path.cwd()] + list(Path.cwd().parents):
        if (root_candidate / ".deepship").exists():
            workspace = str(root_candidate)
            break

    result = evaluate_policy(
        tool=tool_name,
        args=args,
        state=state,
        work_unit=wu,
        workspace=workspace,
    )
    return result.allowed, result.reason
```

Remove obsolete duplicated constants that are no longer used by the hook.

- [ ] **Step 4: Run policy and hook syntax checks**

Run:

```powershell
python -m unittest tests.conformance.test_policy_cases -v
python -m py_compile adapters/cc/hooks/deepship_gate.py
```

Expected: both commands exit 0.

- [ ] **Step 5: Commit**

```powershell
git add adapters/cc/hooks/deepship_gate.py tests/conformance/test_policy_cases.py
git commit -m "refactor: reuse shared policy engine in claude code hook"
```

---

### Task 3: Add Transition Conformance Harness

**Files:**
- Create: `src/deepship/transition.py`
- Create: `tests/conformance/test_transition_cases.py`

- [ ] **Step 1: Write failing transition case runner**

Create `tests/conformance/test_transition_cases.py`:

```python
import json
import unittest
from pathlib import Path

from src.deepship.transition import evaluate_transition


ROOT = Path(__file__).resolve().parents[2]


class TransitionConformanceTest(unittest.TestCase):
    def test_transition_cases(self):
        cases = json.loads(
            (ROOT / "tests" / "conformance" / "transition_cases.json").read_text(encoding="utf-8")
        )["cases"]

        for case in cases:
            with self.subTest(case=case["name"]):
                result = evaluate_transition(
                    from_state=case["from"],
                    to_state=case["to"],
                    context=case.get("context", {}),
                )
                self.assertEqual(case["expected"], result.decision, result.reason)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest tests.conformance.test_transition_cases -v
```

Expected: FAIL with `ModuleNotFoundError` for `src.deepship.transition`.

- [ ] **Step 3: Implement transition evaluator**

Create `src/deepship/transition.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


LEGAL_TRANSITIONS = {
    "READ_CONTEXT": {"CLARIFY_INTENT", "MAP_REALITY"},
    "CLARIFY_INTENT": {"MAP_REALITY", "BLOCK"},
    "MAP_REALITY": {"SELECT_MILESTONE", "BLOCK"},
    "SELECT_MILESTONE": {"PLAN_STEP", "BLOCK"},
    "PLAN_STEP": {"EXECUTE"},
    "EXECUTE": {"VALIDATE"},
    "VALIDATE": {"RECORD", "REPAIR"},
    "REPAIR": {"VALIDATE", "BLOCK"},
    "RECORD": {"ADVANCE"},
    "ADVANCE": {"READ_CONTEXT", "COMPLETE"},
    "BLOCK": set(),
    "COMPLETE": set(),
}


@dataclass(frozen=True)
class TransitionResult:
    decision: str
    reason: str


def _allow(reason: str) -> TransitionResult:
    return TransitionResult("ALLOW", reason)


def _block(reason: str) -> TransitionResult:
    return TransitionResult("BLOCK", reason)


def evaluate_transition(from_state: str, to_state: str, context: dict[str, Any] | None = None) -> TransitionResult:
    context = context or {}
    if to_state not in LEGAL_TRANSITIONS.get(from_state, set()):
        return _block(f"illegal transition {from_state} -> {to_state}")

    if to_state == "EXECUTE":
        if not context.get("current_work_unit"):
            return _block("EXECUTE requires current_work_unit")
        if not context.get("files_allowed"):
            return _block("EXECUTE requires files_allowed")

    if to_state == "VALIDATE" and not context.get("acceptance_tests_ran"):
        return _block("VALIDATE requires at least one acceptance test run")

    if to_state == "ADVANCE" and not context.get("all_work_units_integrated"):
        return _block("ADVANCE requires all work units integrated")

    if to_state == "COMPLETE":
        if not context.get("all_milestones_complete"):
            return _block("COMPLETE requires all milestones complete")
        if not context.get("all_work_units_integrated", True):
            return _block("COMPLETE requires integrated work units")

    if to_state == "REPAIR":
        if not context.get("validation_failed"):
            return _block("REPAIR requires validation failure")
        if int(context.get("repair_attempts", 0)) >= 3:
            return _block("REPAIR attempt limit reached")

    return _allow(f"{from_state} -> {to_state} allowed")
```

- [ ] **Step 4: Run transition tests**

Run:

```powershell
python -m unittest tests.conformance.test_transition_cases -v
```

Expected: PASS for every case in `transition_cases.json`. If case fields differ from `from`, `to`, or `context`, update only the test adapter field extraction, not the protocol semantics.

- [ ] **Step 5: Commit**

```powershell
git add src/deepship/transition.py tests/conformance/test_transition_cases.py
git commit -m "test: add transition conformance harness"
```

---

### Task 4: Add Work Unit and Persistence Conformance

**Files:**
- Create: `src/deepship/persistence.py`
- Create: `tests/conformance/test_work_unit_cases.py`
- Create: `tests/conformance/test_persistence_cases.py`

- [ ] **Step 1: Write work-unit case runner**

Create `tests/conformance/test_work_unit_cases.py`:

```python
import json
import unittest
from pathlib import Path

from src.deepship.persistence import evaluate_work_unit_case


ROOT = Path(__file__).resolve().parents[2]


class WorkUnitConformanceTest(unittest.TestCase):
    def test_work_unit_cases(self):
        cases = json.loads(
            (ROOT / "tests" / "conformance" / "work_unit_cases.json").read_text(encoding="utf-8")
        )["cases"]

        for case in cases:
            with self.subTest(case=case["name"]):
                result = evaluate_work_unit_case(case)
                self.assertEqual(case["expected"], result.decision, result.reason)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Write persistence case runner**

Create `tests/conformance/test_persistence_cases.py`:

```python
import json
import unittest
from pathlib import Path

from src.deepship.persistence import evaluate_persistence_case


ROOT = Path(__file__).resolve().parents[2]


class PersistenceConformanceTest(unittest.TestCase):
    def test_persistence_cases(self):
        cases = json.loads(
            (ROOT / "tests" / "conformance" / "persistence_cases.json").read_text(encoding="utf-8")
        )["cases"]

        for case in cases:
            with self.subTest(case=case["name"]):
                result = evaluate_persistence_case(case)
                self.assertEqual(case["expected"], result.decision, result.reason)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```powershell
python -m unittest tests.conformance.test_work_unit_cases tests.conformance.test_persistence_cases -v
```

Expected: FAIL with missing `src.deepship.persistence`.

- [ ] **Step 4: Implement persistence helpers**

Create `src/deepship/persistence.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


VALID_WU_STATUS = {"pending", "in_progress", "done", "integrated", "blocked", "failed"}
VALID_RESULT = {"ok", "fail", "blocked"}
VALID_STATES = {
    "READ_CONTEXT", "CLARIFY_INTENT", "MAP_REALITY", "SELECT_MILESTONE",
    "PLAN_STEP", "EXECUTE", "VALIDATE", "REPAIR", "RECORD", "ADVANCE",
    "BLOCK", "COMPLETE",
}


@dataclass(frozen=True)
class ConformanceResult:
    decision: str
    reason: str


def _allow(reason: str) -> ConformanceResult:
    return ConformanceResult("ALLOW", reason)


def _block(reason: str) -> ConformanceResult:
    return ConformanceResult("BLOCK", reason)


def _has_iso_datetime(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def validate_work_unit(work_unit: dict[str, Any]) -> ConformanceResult:
    if not work_unit.get("id"):
        return _block("work unit id is required")
    if not work_unit.get("goal"):
        return _block("work unit goal is required")
    if not work_unit.get("owner"):
        return _block("work unit owner is required")
    if work_unit.get("status") not in VALID_WU_STATUS:
        return _block("invalid work unit status")
    if not work_unit.get("files_allowed"):
        return _block("files_allowed must not be empty")
    return _allow("valid work unit")


def validate_state(state: dict[str, Any]) -> ConformanceResult:
    if state.get("current_state") not in VALID_STATES:
        return _block("invalid current_state")
    if not _has_iso_datetime(state.get("updated_at")):
        return _block("updated_at must be ISO 8601")
    validation_status = state.get("validation_status")
    if validation_status not in (None, "passed", "failed"):
        return _block("invalid validation_status")
    return _allow("valid state")


def validate_log_record(record: dict[str, Any]) -> ConformanceResult:
    if record.get("init") is True:
        return _allow("valid init record") if _has_iso_datetime(record.get("timestamp")) else _block("init timestamp required")
    if record.get("from_state") not in VALID_STATES:
        return _block("invalid from_state")
    if record.get("to_state") not in VALID_STATES:
        return _block("invalid to_state")
    if record.get("result") not in VALID_RESULT:
        return _block("invalid result")
    if not _has_iso_datetime(record.get("timestamp")):
        return _block("timestamp must be ISO 8601")
    return _allow("valid log record")


def evaluate_work_unit_case(case: dict[str, Any]) -> ConformanceResult:
    work_unit = case.get("work_unit") or case.get("input") or {}
    return validate_work_unit(work_unit)


def evaluate_persistence_case(case: dict[str, Any]) -> ConformanceResult:
    kind = case.get("kind") or case.get("type")
    payload = case.get("payload") or case.get("input") or {}
    if kind == "state":
        return validate_state(payload)
    if kind == "log":
        return validate_log_record(payload)
    if kind == "work_unit":
        return validate_work_unit(payload)
    return _block("unknown persistence case kind")
```

- [ ] **Step 5: Run persistence-related tests**

Run:

```powershell
python -m unittest tests.conformance.test_work_unit_cases tests.conformance.test_persistence_cases -v
```

Expected: PASS for all current cases. If current fixture field names differ, adapt `evaluate_*_case()` to consume the fixture shape while preserving the protocol constraints.

- [ ] **Step 6: Commit**

```powershell
git add src/deepship/persistence.py tests/conformance/test_work_unit_cases.py tests/conformance/test_persistence_cases.py
git commit -m "test: add work unit and persistence conformance harness"
```

---

### Task 5: Wire Conformance Into Self-Verification

**Files:**
- Modify: `checks/verify.py`
- Test: `checks/verify.py`

- [ ] **Step 1: Add failing expectation to verification**

Modify `checks/verify.py` to add this helper near the other check functions:

```python
def check_runnable_conformance():
    print("\n[11] Runnable conformance suite")
    import subprocess

    cmd = [sys.executable, "-m", "unittest", "discover", "-s", "tests/conformance", "-p", "test_*.py", "-v"]
    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    if result.returncode == 0:
        ok("runnable conformance suite passed")
    else:
        err("runnable conformance suite failed")
        print(result.stdout)
        print(result.stderr)
```

Call it in `__main__` after `check_protocol_integrity()`:

```python
    check_runnable_conformance()
```

- [ ] **Step 2: Run full verification**

Run:

```powershell
python checks/verify.py
```

Expected: PASS or PASS with existing warnings. Any new failure must name the conformance suite output.

- [ ] **Step 3: Commit**

```powershell
git add checks/verify.py
git commit -m "test: run conformance suite from framework verification"
```

---

### Task 6: Update Adapter Documentation

**Files:**
- Modify: `adapters/claude-code/README.md`
- Modify: `adapters/mate/README.md`

- [ ] **Step 1: Update Claude Code adapter README**

Add `## Conformance` to `adapters/claude-code/README.md` stating:

- The adapter delegates policy decisions to `src/deepship/policy.py`.
- Level 1 Policy compatibility requires `tests/conformance/test_policy_cases.py` passing.
- Higher levels require transition, work-unit, and persistence tests passing.
- Verification commands are:

```powershell
python -m unittest discover -s tests/conformance -p "test_*.py" -v
python checks/verify.py
```

- [ ] **Step 2: Update Mate adapter README**

Add `## Conformance` to `adapters/mate/README.md` stating that Mate runtimes must pass `tests/conformance/`, and that `src/deepship/` is protocol test support rather than the only valid runtime architecture.

- [ ] **Step 3: Run verification checks**

Run:

```powershell
python checks/verify.py
```

Expected: PASS or PASS with pre-existing warnings only.

- [ ] **Step 4: Commit**

```powershell
git add adapters/claude-code/README.md adapters/mate/README.md
git commit -m "docs: document adapter conformance workflow"
```

---

## Final Validation

- [ ] Run:
  `python -m unittest tests.conformance.test_policy_cases -v`
- [ ] Run:
  `python -m unittest discover -s tests/conformance -p "test_*.py" -v`
- [ ] Run:
  `python checks/verify.py`
- [ ] Inspect:
  `git status --short`
- [ ] Inspect:
  `git diff -- src tests adapters checks`
- [ ] Expected final state: all runnable conformance tests pass, `checks/verify.py` has no new failures, the Claude Code hook imports shared policy behavior, and adapter docs state exact compatibility commands.

## Residual Risks

- Existing fixture shapes may not match this plan's field assumptions; adapt the thin test layer without changing protocol semantics.
- `jsonschema` is intentionally deferred to a separate dependency-management milestone.
- Claude Code hook consistency improves, but hard enforcement still depends on runtime-level tool interception.
