import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STATUSLINE_PATH = ROOT / "adapters" / "cc" / "statusline.py"


def load_statusline():
    spec = importlib.util.spec_from_file_location("deepship_statusline", STATUSLINE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ClaudeCodeStatusLineTest(unittest.TestCase):
    def test_non_deepship_workspace_renders_empty_line(self):
        statusline = load_statusline()
        with tempfile.TemporaryDirectory() as tmp:
            rendered = statusline.render({"cwd": tmp, "columns": 120})

        self.assertEqual(rendered, "")

    def test_renders_current_state_milestone_and_work_unit_progress(self):
        statusline = load_statusline()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            deepship = root / ".deepship"
            deepship.mkdir()
            (deepship / "state.json").write_text(
                json.dumps(
                    {
                        "current_state": "EXECUTE",
                        "current_milestone": "rotate-v0.2",
                        "current_work_unit": "WU-IR03",
                    }
                ),
                encoding="utf-8",
            )
            (deepship / "work_units.json").write_text(
                json.dumps(
                    {
                        "work_units": [
                            {"id": "WU-IR01", "status": "integrated"},
                            {"id": "WU-IR02", "status": "pending"},
                            {"id": "WU-IR03", "status": "in_progress"},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            rendered = statusline.render(
                {
                    "cwd": str(root),
                    "columns": 120,
                    "context_window": {"used_percentage": 8},
                }
            )

        self.assertIn("DEEPSHIP EXECUTE", rendered)
        self.assertIn("rotate-v0.2", rendered)
        self.assertIn("WU-IR03:in_progress", rendered)
        self.assertIn("1/3 integrated", rendered)
        self.assertIn("ctx 8%", rendered)

    def test_renders_within_available_columns(self):
        statusline = load_statusline()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            deepship = root / ".deepship"
            deepship.mkdir()
            (deepship / "state.json").write_text(
                json.dumps(
                    {
                        "current_state": "PLAN_STEP",
                        "current_milestone": "very-long-milestone-name-for-terminal-width",
                        "current_work_unit": "WU-LONG",
                    }
                ),
                encoding="utf-8",
            )
            (deepship / "work_units.json").write_text(
                json.dumps({"work_units": [{"id": "WU-LONG", "status": "pending"}]}),
                encoding="utf-8",
            )

            rendered = statusline.render({"cwd": str(root), "columns": 36})

        self.assertLessEqual(len(rendered), 36)
        self.assertTrue(rendered.endswith("..."))


if __name__ == "__main__":
    unittest.main()
