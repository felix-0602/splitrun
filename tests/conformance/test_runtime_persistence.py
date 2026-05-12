import json
import tempfile
import unittest
from pathlib import Path

from adapters.cc import transition_state
from init_deepship import init_deepship


class RuntimePersistenceConformance(unittest.TestCase):
    def test_init_deepship_creates_empty_runtime_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            created = init_deepship(root)

            self.assertEqual(
                sorted(path.relative_to(root).as_posix() for path in created),
                [".deepship/log.jsonl", ".deepship/state.json", ".deepship/work_units.json"],
            )
            state = json.loads((root / ".deepship" / "state.json").read_text(encoding="utf-8"))
            work_units = json.loads((root / ".deepship" / "work_units.json").read_text(encoding="utf-8"))
            self.assertEqual(state["current_state"], "READ_CONTEXT")
            self.assertEqual(work_units["work_units"], [])
            self.assertEqual((root / ".deepship" / "log.jsonl").read_text(encoding="utf-8"), "")

    def test_record_transition_recovers_pending_records_and_clears_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_deepship(root)
            (root / ".deepship" / "state.json").write_text(
                json.dumps({"current_state": "VALIDATE", "current_work_unit": "WU-001"}),
                encoding="utf-8",
            )

            transition_state.write_pending_record(root, "note", "keep this", {"wu": "WU-001"})
            result = transition_state.transition("RECORD", project_root=root)

            self.assertTrue(result["success"], result)
            self.assertEqual((root / ".deepship" / "pending_records.jsonl").read_text(encoding="utf-8"), "")
            self.assertIn("keep this", (root / "Documentation.md").read_text(encoding="utf-8"))

    def test_advance_to_complete_blocks_when_pending_work_units_remain(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_deepship(root)
            (root / ".deepship" / "state.json").write_text(
                json.dumps({"current_state": "ADVANCE", "current_work_unit": "WU-001"}),
                encoding="utf-8",
            )
            (root / ".deepship" / "work_units.json").write_text(
                json.dumps(
                    {
                        "work_units": [
                            {"id": "WU-001", "status": "integrated"},
                            {"id": "WU-002", "status": "pending"},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = transition_state.transition("COMPLETE", project_root=root)

            self.assertFalse(result["success"], result)
            self.assertIn("WU-002", result["reason"])


if __name__ == "__main__":
    unittest.main()
