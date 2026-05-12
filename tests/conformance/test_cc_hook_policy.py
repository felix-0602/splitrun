import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HOOK_PATH = ROOT / "adapters" / "cc" / "hooks" / "deepship_gate.py"
CASES_PATH = ROOT / "tests" / "conformance" / "policy_cases.json"


def load_hook():
    spec = importlib.util.spec_from_file_location("deepship_gate", HOOK_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ClaudeCodeHookPolicyConformance(unittest.TestCase):
    def test_policy_cases(self):
        hook = load_hook()
        cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))["cases"]
        failures = []

        for case in cases:
            state = {
                "current_state": case["state"],
                "workspace": case.get("workspace"),
                "validation_status": case.get("args", {}).get("validation_status"),
            }
            wu = case.get("work_unit")
            allowed, reason = hook.evaluate(case["tool"], case["args"], state, wu)
            actual = "ALLOW" if allowed else "BLOCK"
            if actual != case["expected"]:
                failures.append(f"{case['name']}: expected {case['expected']}, got {actual} ({reason})")

        self.assertFalse(failures, "\n".join(failures))


if __name__ == "__main__":
    unittest.main()
