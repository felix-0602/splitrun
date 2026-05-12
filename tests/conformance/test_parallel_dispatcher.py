import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from adapters.parallel import dispatcher


class ParallelDispatcherTest(unittest.TestCase):
    def test_no_monitor_returns_without_detach_requirement(self):
        class FakeProcess:
            pass

        work_units = [
            {
                "id": "WU-001",
                "status": "pending",
                "execution_mode": "inline",
                "files_allowed": ["src/a.py"],
                "acceptance_tests": [],
            }
        ]

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wt_path = root / "wt"
            wt_path.mkdir()

            with (
                patch.object(dispatcher, "_check_wt_available", return_value=True),
                patch.object(dispatcher, "load_work_units", return_value=work_units),
                patch.object(dispatcher, "create_worktree", return_value=wt_path),
                patch.object(dispatcher, "spawn_terminal", return_value=FakeProcess()),
            ):
                result = dispatcher.dispatch(project_root=root, no_monitor=True)

        self.assertEqual(result, {})


if __name__ == "__main__":
    unittest.main()
