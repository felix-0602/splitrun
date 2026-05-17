"""
Scope recommendation contract tests — splitrun-scope 机器可读契约。

核心契约: recommendation 字段必须是 'spawn' 或 'do_not_spawn'（下划线）。
splitrun-spawn 依赖该字段做前置检查，任何格式偏差都会破坏 spawn。
"""

import unittest
from adapters.gates import parse_recommendation


class ScopeRecommendationTest(unittest.TestCase):
    """recommendation 字段解析契约。"""

    def test_parse_spawn(self):
        text = "## 建议\nrecommendation: spawn\n\n理由: 适合并行"
        self.assertEqual(parse_recommendation(text), "spawn")

    def test_parse_do_not_spawn(self):
        text = "## 建议\nrecommendation: do_not_spawn\n\n理由: 依赖太多"
        self.assertEqual(parse_recommendation(text), "do_not_spawn")

    def test_parse_with_extra_whitespace(self):
        text = "recommendation:  spawn  \n"
        self.assertEqual(parse_recommendation(text), "spawn")

    def test_rejects_no_underscore(self):
        """'do not spawn'（空格，旧版不一致写法）不被接受 —— 必须用下划线。"""
        text = "recommendation: do not spawn\n"
        self.assertIsNone(parse_recommendation(text))

    def test_rejects_unknown_value(self):
        text = "recommendation: maybe_later\n"
        self.assertIsNone(parse_recommendation(text))

    def test_rejects_missing_colon(self):
        text = "recommendation spawn\n"
        self.assertIsNone(parse_recommendation(text))

    def test_not_found_returns_none(self):
        text = "## 建议\n还没有决定\n"
        self.assertIsNone(parse_recommendation(text))

    def test_full_scope_document(self):
        """同真实 scope.md 模板格式一致。"""
        text = """# Scope: 重构 auth 模块

## 已确认事实
- src/auth.py 存在
- 测试在 tests/test_auth.py

## 建议
recommendation: spawn

理由: 文件边界清晰，无外部依赖
"""
        self.assertEqual(parse_recommendation(text), "spawn")

    def test_spawn_skill_contract(self):
        """确保 spawn 技能文档中的 'do not spawn' 会被正确拒绝，
        从而迫使技能文档与 scope 契约保持一致。"""
        # spawn 技能预期检查 do_not_spawn（下划线）
        self.assertEqual(parse_recommendation("recommendation: do_not_spawn"), "do_not_spawn")
        # 如果写成了 do not spawn（空格），parse 返回 None
        self.assertIsNone(parse_recommendation("recommendation: do not spawn"))


if __name__ == "__main__":
    unittest.main()
