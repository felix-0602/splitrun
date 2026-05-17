"""
Boundary check contract tests — splitrun-land Step 2 硬门禁。

核心契约: changed_files ⊆ files_claimed
越界必须被检测，且检测结果可被 land 和 status 消费。
"""

import unittest
from adapters.gates import check_boundary, claim_matches


class ClaimMatchingTest(unittest.TestCase):
    """claim_matches 基元 —— 文件路径匹配逻辑。"""

    def test_exact_match(self):
        self.assertTrue(claim_matches("src/auth.py", "src/auth.py"))

    def test_prefix_directory_match(self):
        """claimed 'dir/' 匹配目录下所有文件。"""
        self.assertTrue(claim_matches("src/", "src/auth.py"))
        self.assertTrue(claim_matches("src/", "src/sub/file.py"))

    def test_no_false_prefix_match(self):
        """'src/a.py' 不应匹配 'src/auth.py'（仅前缀相同时）。"""
        self.assertFalse(claim_matches("src/a.py", "src/auth.py"))

    def test_glob_wildcard_match(self):
        self.assertTrue(claim_matches("src/*.py", "src/auth.py"))
        self.assertFalse(claim_matches("src/*.py", "src/data.json"))

    def test_empty_pattern_never_matches(self):
        self.assertFalse(claim_matches("", "src/auth.py"))
        self.assertFalse(claim_matches("src/auth.py", ""))

    def test_normalized_backslashes(self):
        """Windows 反斜杠应被标准化。"""
        self.assertTrue(claim_matches("src\\auth.py", "src/auth.py"))
        self.assertTrue(claim_matches("src/auth.py", "src\\auth.py"))


class BoundaryCheckTest(unittest.TestCase):
    """check_boundary 门禁契约。"""

    def test_all_in_bounds_passes(self):
        result = check_boundary(
            changed_files=["src/auth.py", "src/login.py"],
            files_claimed=["src/"],
        )
        self.assertTrue(result["pass"])
        self.assertEqual(result["out_of_bounds"], [])
        self.assertEqual(set(result["in_bounds"]), {"src/auth.py", "src/login.py"})

    def test_out_of_bounds_detected(self):
        result = check_boundary(
            changed_files=["src/auth.py", "utils/helper.py"],
            files_claimed=["src/"],
        )
        self.assertFalse(result["pass"])
        self.assertIn("utils/helper.py", result["out_of_bounds"])
        self.assertIn("src/auth.py", result["in_bounds"])

    def test_all_out_of_bounds(self):
        result = check_boundary(
            changed_files=["utils/a.py", "utils/b.py"],
            files_claimed=["src/"],
        )
        self.assertFalse(result["pass"])
        self.assertEqual(len(result["out_of_bounds"]), 2)
        self.assertEqual(len(result["in_bounds"]), 0)

    def test_empty_changed_files_passes(self):
        """没有改动 = 无越界。"""
        result = check_boundary(
            changed_files=[],
            files_claimed=["src/"],
        )
        self.assertTrue(result["pass"])

    def test_empty_claimed_triggers_boundary(self):
        """没有 claimed 时，所有改动都是越界。"""
        result = check_boundary(
            changed_files=["src/auth.py"],
            files_claimed=[],
        )
        self.assertFalse(result["pass"])
        self.assertIn("src/auth.py", result["out_of_bounds"])

    def test_multiple_claims_any_match(self):
        """多个 claimed pattern，任一匹配即算在界内。"""
        result = check_boundary(
            changed_files=["src/auth.py", "docs/readme.md", "tests/test_auth.py"],
            files_claimed=["src/", "tests/"],
        )
        self.assertFalse(result["pass"])
        self.assertIn("docs/readme.md", result["out_of_bounds"])

    def test_glob_claim(self):
        """通配符 claim 正确匹配。"""
        result = check_boundary(
            changed_files=["src/auth.py", "src/data.json"],
            files_claimed=["src/*.py"],
        )
        self.assertFalse(result["pass"])
        self.assertIn("src/data.json", result["out_of_bounds"])
        self.assertIn("src/auth.py", result["in_bounds"])


if __name__ == "__main__":
    unittest.main()
