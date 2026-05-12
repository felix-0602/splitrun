#!/usr/bin/env python3
"""
DEEPSHIP Parallel Collector v0.1 — 回收 worker 的 result.json 并验证.

读取各 worktree 的 .deepship/runs/<wu_id>/result.json，
逐项验证边界、测试覆盖、冲突，输出通过/失败报告。

验证规则：
  - changed_files 全部在 files_allowed 内（边界检查）
  - tests_run 至少覆盖 acceptance_tests 中的一条（测试检查）
  - result.json 结构完整（格式检查）
  - 无跨 WU 文件冲突（冲突检查）
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

# 支持直接执行 python collector.py 或 python -m adapters.parallel.collector
try:
    from adapters.parallel.dispatcher import (
        DEEPSHIP_DIR,
        RUNS_DIR,
        WORKTREE_PARENT,
        WU_ID_PATTERN,
        _validate_wu_id,
        find_deepship_root,
        load_work_units,
    )
except ModuleNotFoundError:
    _here = Path(__file__).resolve().parents[2]
    if str(_here) not in sys.path:
        sys.path.insert(0, str(_here))
    from adapters.parallel.dispatcher import (
        DEEPSHIP_DIR,
        RUNS_DIR,
        WORKTREE_PARENT,
        WU_ID_PATTERN,
        _validate_wu_id,
        find_deepship_root,
        load_work_units,
    )

# ── 校验函数 ────────────────────────────────────────────


def validate_boundary(result: dict, wu: dict) -> list[str]:
    """检查 changed_files 是否全部在 files_allowed 内。返回违规列表。"""
    allowed = set(wu.get("files_allowed", []))
    if not allowed:
        return []  # 没有 files_allowed 定义，跳过边界检查

    changed = set(result.get("changed_files", []))
    violations = []
    for f in changed:
        # 规范化路径
        f_norm = f.replace("\\", "/")
        matched = any(
            f_norm == a.replace("\\", "/")
            or f_norm.startswith(a.replace("\\", "/").rstrip("/") + "/")
            for a in allowed
        )
        if not matched:
            violations.append(f)
    return violations


def validate_tests(result: dict, wu: dict) -> tuple[bool, str]:
    """检查是否跑了测试。不强制全部通过，但必须至少跑了一条。"""
    acceptance = wu.get("acceptance_tests", [])
    tests_run = result.get("tests_run", [])

    if not acceptance:
        return True, "（未定义验收测试，跳过）"

    if not tests_run:
        return False, "未运行任何测试"

    # 宽松匹配：tests_run 中至少有一条与 acceptance_tests 中某条相关
    matched = any(
        any(at.lower() in tr.lower() or tr.lower() in at.lower() for at in acceptance)
        for tr in tests_run
    )
    if matched:
        return True, f"已运行 {len(tests_run)} 条测试"
    else:
        return False, f"tests_run 与 acceptance_tests 不匹配"


def validate_format(result: dict, wu_id: str) -> list[str]:
    """检查 result.json 结构完整性。返回缺失字段列表。"""
    required = ["wu_id", "status", "changed_files", "tests_run", "summary"]
    missing = [f for f in required if f not in result]

    if "status" in result and result["status"] not in ("done", "failed"):
        missing.append(f"status 值不合法: {result['status']}（应为 done 或 failed）")

    if "wu_id" in result and result["wu_id"] != wu_id:
        missing.append(f"wu_id 不匹配: 期望 {wu_id}，实际 {result['wu_id']}")

    return missing


# ── 收集 ────────────────────────────────────────────────


def collect_results(
    project_root: Path,
    wu_ids: list[str] | None = None,
) -> dict[str, dict]:
    """读取所有 worktree 的 result.json。返回 {wu_id: result}。"""
    results: dict[str, dict] = {}

    if wu_ids is None:
        # 自动发现：扫描 worktree 父目录
        wt_parent = project_root.parent / WORKTREE_PARENT
        if not wt_parent.exists():
            print(f"[COLLECT] worktree 父目录不存在: {wt_parent}")
            return {}

        for wt_dir in sorted(wt_parent.iterdir()):
            if not wt_dir.is_dir():
                continue
            wu_id = wt_dir.name
            result_file = wt_dir / DEEPSHIP_DIR / RUNS_DIR / wu_id / "result.json"
            if result_file.exists():
                try:
                    results[wu_id] = json.loads(result_file.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError) as e:
                    print(f"  [WARN] {wu_id}: result.json 读取失败 —— {e}")
    else:
        for wu_id in wu_ids:
            wt_dir = project_root.parent / WORKTREE_PARENT / wu_id
            result_file = wt_dir / DEEPSHIP_DIR / RUNS_DIR / wu_id / "result.json"
            if result_file.exists():
                try:
                    results[wu_id] = json.loads(result_file.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError) as e:
                    print(f"  [WARN] {wu_id}: result.json 读取失败 —— {e}")

    return results


# ── 冲突检查 ────────────────────────────────────────────


def check_conflicts(results: dict[str, dict], wus: list[dict]) -> list[str]:
    """检查多个 worker 是否修改了同一文件（跨 WU 冲突）。返回冲突文件列表。"""
    file_owners: dict[str, str] = {}
    conflicts: list[str] = []

    for wu_id, result in results.items():
        for f in result.get("changed_files", []):
            f_norm = f.replace("\\", "/")
            if f_norm in file_owners:
                conflicts.append(f"{f_norm}（{file_owners[f_norm]} 和 {wu_id} 都改了）")
            else:
                file_owners[f_norm] = wu_id

    return conflicts


# ── 主入口 ──────────────────────────────────────────────


def collect(
    project_root: Path | None = None,
    wu_filter: list[str] | None = None,
) -> dict[str, dict]:
    """主入口：收集 → 验证 → 报告。返回 {wu_id: {result, validations}}。"""
    root = project_root or find_deepship_root()
    if root is None:
        print("[ERROR] 未找到 .deepship/ 目录。")
        sys.exit(1)

    print(f"[COLLECT] 项目根目录: {root}")

    all_wus = load_work_units(root)
    if not all_wus:
        print("[ERROR] 没有 work unit。")
        sys.exit(1)

    wu_map = {w["id"]: w for w in all_wus}

    # 收集 result.json
    results = collect_results(root, wu_filter)
    if not results:
        print("[COLLECT] 未找到任何 result.json。worker 可能尚未完成。")
        print(f"         预期位置: {root.parent / WORKTREE_PARENT}/<WU-ID>/{DEEPSHIP_DIR}/{RUNS_DIR}/<WU-ID>/result.json")
        return {}

    print(f"[COLLECT] 收集到 {len(results)} 个结果\n")

    # 逐 WU 验证
    all_ok = True
    combined: dict[str, dict] = {}

    for wu_id, result in sorted(results.items()):
        wu = wu_map.get(wu_id, {})
        issues: list[str] = []

        # 格式检查
        fmt_issues = validate_format(result, wu_id)
        issues.extend(fmt_issues)

        # 边界检查
        boundary_violations = validate_boundary(result, wu)
        if boundary_violations:
            issues.append(f"越界文件: {boundary_violations}")

        # 测试检查
        tests_ok, tests_msg = validate_tests(result, wu)
        if not tests_ok:
            issues.append(f"测试不足: {tests_msg}")

        status = result.get("status", "?")
        icon = "PASS" if not issues and status == "done" else "FAIL"

        print(f"  [{icon}] {wu_id}")
        print(f"       目标: {wu.get('goal', '?')}")
        print(f"       状态: {status}")
        print(f"       文件: {result.get('changed_files', [])}")
        print(f"       测试: {result.get('tests_run', [])}")
        if result.get("risks"):
            print(f"       风险: {result.get('risks')}")
        if issues:
            for issue in issues:
                print(f"       ⚠ {issue}")
            all_ok = False
        if result.get("summary"):
            print(f"       总结: {result['summary']}")
        print()

        combined[wu_id] = {
            "result": result,
            "valid": len(issues) == 0 and status == "done",
            "issues": issues,
        }

    # 冲突检查
    conflicts = check_conflicts(results, all_wus)
    if conflicts:
        all_ok = False
        print("  [CONFLICT] 跨 WU 文件冲突:")
        for c in conflicts:
            print(f"    ⚠ {c}")
        print()

    # 汇总
    print("=" * 60)
    valid_count = sum(1 for v in combined.values() if v["valid"])
    print(f"  收集: {len(results)} 个 worker 结果")
    print(f"  通过: {valid_count}")
    print(f"  未通过: {len(results) - valid_count}")
    if conflicts:
        print(f"  冲突: {len(conflicts)} 个文件")

    if all_ok:
        print(f"\n  所有 worker 验证通过。主线程可以集成。")
        print(f"  下一步: VALIDATE → 合并 worktree 变更 → RECORD")
    else:
        print(f"\n  存在未通过项。修复后再集成。")
        print(f"  修复路径: 进入 REPAIR 或重新分派失败的 WU")

    print("=" * 60)

    return combined


# ── 合并辅助 ────────────────────────────────────────────


def show_unmerged_diff(project_root: Path, wu_ids: list[str]) -> None:
    """展示各 worktree 中未合并的 diff（给主线程参考）。"""
    for wu_id in wu_ids:
        wt_path = project_root.parent / WORKTREE_PARENT / wu_id
        if not wt_path.exists():
            continue
        try:
            result = subprocess.run(
                ["git", "-C", str(wt_path), "diff", "HEAD"],
                capture_output=True, text=True, timeout=10,
            )
            if result.stdout.strip():
                print(f"\n── {wu_id} diff ──")
                print(result.stdout[:2000])  # 截断，避免刷屏
        except Exception:
            pass


# ── 合并 ────────────────────────────────────────────────


def apply_worktree(wt_path: Path, wu_id: str, project_root: Path) -> tuple[bool, str]:
    """将 worktree 的变更以 patch 方式合入主仓库。

    流程：git diff HEAD → 保存 .deepship/runs/<wu_id>/changes.patch → git apply。
    即使 apply 失败，patch 文件也会保留，可手动处理。
    """
    # 生成 diff
    diff_result = subprocess.run(
        ["git", "-C", str(wt_path), "diff", "HEAD"],
        capture_output=True, text=True, timeout=10,
    )
    diff_text = diff_result.stdout.strip()
    if not diff_text:
        return True, "（无变更）"

    # 保存 patch 到主仓库的 runs 目录（供手动修复）
    patch_dir = project_root / DEEPSHIP_DIR / RUNS_DIR / wu_id
    patch_dir.mkdir(parents=True, exist_ok=True)
    patch_file = patch_dir / "changes.patch"
    patch_file.write_text(diff_text, encoding="utf-8")

    # 应用到主仓库
    apply_result = subprocess.run(
        ["git", "-C", str(project_root), "apply", "--whitespace=nowarn", str(patch_file)],
        capture_output=True, text=True, timeout=10,
    )

    if apply_result.returncode == 0:
        return True, f"已合入 {len(diff_text.splitlines())} 行变更"
    else:
        err = apply_result.stderr.strip()[:200]
        return False, f"git apply 失败: {err}\n  patch 已保存到 {patch_file}，手动处理。"


def apply_all(combined: dict[str, dict], project_root: Path) -> dict[str, bool]:
    """对所有验证通过的 WU 执行 apply。返回 {wu_id: success}。"""
    results: dict[str, bool] = {}
    print("\n[APPLY] 合并 worktree 变更...")

    for wu_id, entry in sorted(combined.items()):
        if not entry["valid"]:
            print(f"  [SKIP] {wu_id} —— 验证未通过")
            results[wu_id] = False
            continue

        wt_path = project_root.parent / WORKTREE_PARENT / wu_id
        if not wt_path.exists():
            print(f"  [SKIP] {wu_id} —— worktree 不存在")
            results[wu_id] = False
            continue

        ok, msg = apply_worktree(wt_path, wu_id, project_root)
        icon = "OK" if ok else "!!"
        print(f"  [{icon}] {wu_id}: {msg}")
        results[wu_id] = ok

    return results


# ── CLI ─────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="DEEPSHIP Parallel Collector v0.1 —— 回收、验证、合并 worker 结果",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
示例:
  python adapters/parallel/collector.py                           # 仅收集验证
  python adapters/parallel/collector.py --apply                   # 验证 + 合并 patch
  python adapters/parallel/collector.py --apply --cleanup          # 验证 + 合并 + 清理 worktree
  python adapters/parallel/collector.py --apply --cleanup --force  # 即使合并失败也清理
  python adapters/parallel/collector.py --show-diff               # 展示未合并 diff
        """,
    )
    parser.add_argument(
        "--wu",
        type=str,
        help="逗号分隔的 WU ID（默认：自动发现所有 worktree）",
    )
    parser.add_argument(
        "--project-root", "-d",
        type=str,
        help="项目根目录（默认：从当前目录自动检测）",
    )
    parser.add_argument(
        "--show-diff",
        action="store_true",
        help="展示各 worktree 的未合并 diff",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="验证通过后将 worktree 变更以 patch 方式合入主仓库",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="清理 worktree（必须与 --apply 一起使用，除非 --force）",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="即使 apply 失败也执行 cleanup（危险：可能丢失 worker 改动）",
    )

    args = parser.parse_args()

    # 安全检查：--cleanup 必须配合 --apply（除非 --force）
    if args.cleanup and not args.apply and not args.force:
        print("[ERROR] --cleanup 需要 --apply（先合并再清理）或 --force（强制清理）。")
        print("        worker 的改动在 worktree 中，未合并就清理 = 丢失改动。")
        print("        正确用法: python adapters/parallel/collector.py --apply --cleanup")
        sys.exit(1)

    root = Path(args.project_root) if args.project_root else None
    wu_filter = args.wu.split(",") if args.wu else None

    combined = collect(project_root=root, wu_filter=wu_filter)

    if args.show_diff and combined:
        wu_ids = list(combined.keys())
        root_resolved = root or find_deepship_root()
        if root_resolved:
            show_unmerged_diff(root_resolved, wu_ids)

    # Apply（先合并，再清理）
    if args.apply and combined:
        root_resolved = root or find_deepship_root()
        if root_resolved:
            apply_results = apply_all(combined, root_resolved)

    if args.cleanup and combined:
        from adapters.parallel.dispatcher import cleanup_worktrees
        root_resolved = root or find_deepship_root()
        if root_resolved:
            if args.force:
                # 强制清理：不管 apply 是否成功
                cleanup_worktrees(root_resolved, list(combined.keys()))
            elif args.apply:
                # 只清理 apply 成功的 worktree
                ok_ids = [wid for wid, ok in apply_results.items() if ok]
                fail_ids = [wid for wid, ok in apply_results.items() if not ok]
                if ok_ids:
                    cleanup_worktrees(root_resolved, ok_ids)
                if fail_ids:
                    print(f"[COLLECT] 以下 WU 合并失败，保留 worktree 供手动处理: {fail_ids}")
            else:
                print("[COLLECT] --cleanup 需要 --apply 或 --force。")


if __name__ == "__main__":
    main()
