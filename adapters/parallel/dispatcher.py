#!/usr/bin/env python3
"""
DEEPSHIP Parallel Terminal Dispatcher v0.1 — 固定 runner + git worktree 隔离.

读取 .deepship/work_units.json，为互不依赖的 WU 各自创建 git worktree，
生成 worker prompt，启动独立终端窗口指向各自的 worktree。

Worker 只在自己的 worktree 里干活，产出 result.json。
主线程用 collector.py 回收、验证、集成。
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

# ── 常量 ────────────────────────────────────────────────

DEEPSHIP_DIR = ".deepship"
WU_FILE = "work_units.json"
RUNS_DIR = "runs"
WORKTREE_PARENT = ".deepship-worktrees"

ALLOWED_TOOLS = "Read,Write,Edit,Bash,Glob,Grep,Task,Skill,Agent"
WU_ID_PATTERN = r"^WU-\d{3}$"
POLL_INTERVAL = 5.0

# Worker 的聚焦 prompt 模板
PROMPT_TEMPLATE = """\
你正在执行 DEEPSHIP **Work Unit {wu_id}**，运行在独立的 git worktree 中。

## 工作单元定义

**目标：** {goal}

**范围：** {scope}

**允许修改的文件：** {files_allowed}

**验收测试：**
{acceptance_tests}

## 项目上下文
{project_context}

## 执行协议

1. **Read** 你需要理解的任何文件
2. **Implement** 达成目标所需的修改 —— 严格限定在 `files_allowed` 内
3. **Test** 你的修改，跑验收测试
4. **写入结果** 到 `.deepship/runs/{wu_id}/result.json`，格式如下：

```json
{{
  "wu_id": "{wu_id}",
  "status": "done | failed",
  "changed_files": ["修改的文件路径列表"],
  "tests_run": ["运行的测试命令列表"],
  "summary": "一句话总结做了什么",
  "risks": "任何风险或已知问题，没有则填 null"
}}
```

## 硬约束

- 只能改 `files_allowed` 中列出的文件
- 不能改 `.deepship/state.json`、`.deepship/work_units.json`、`.deepship/log.jsonl`
- 不能扩大 scope
- 遇到阻塞问题 → status 写 `failed`，summary 写原因
- 你运行在独立的 git worktree 中，改文件不会影响主工作区

开始执行。自主工作直到完成或阻塞。"""

# PowerShell 启动模板（claude -p 模式）
PS_LAUNCHER = """\
$prompt = Get-Content '{prompt_file}' -Raw -Encoding UTF8
claude -p $prompt {extra_flags}
"""


# ── 校验 ────────────────────────────────────────────────

def _validate_wu_id(wu_id: str) -> bool:
    return bool(re.match(WU_ID_PATTERN, wu_id))


# ── 根目录发现 ──────────────────────────────────────────

def find_deepship_root(start: Path | None = None) -> Path | None:
    for candidate in [start or Path.cwd()] + list((start or Path.cwd()).parents):
        if (candidate / DEEPSHIP_DIR).is_dir():
            return candidate
    return None


# ── WU 加载 ─────────────────────────────────────────────

def load_work_units(root: Path) -> list[dict[str, Any]]:
    wu_path = root / DEEPSHIP_DIR / WU_FILE
    if not wu_path.exists():
        print(f"[ERROR] {wu_path} 不存在。请先执行 PLAN_STEP。")
        return []
    data = json.loads(wu_path.read_text(encoding="utf-8"))
    return data.get("work_units", [])


# ── 并行分组 ────────────────────────────────────────────

def _files_overlap(a: list[str], b: list[str]) -> bool:
    a_set = {p.replace("\\", "/").rstrip("/") for p in a}
    b_set = {p.replace("\\", "/").rstrip("/") for p in b}
    for fa in a_set:
        for fb in b_set:
            if fa == fb or fa.startswith(fb + "/") or fb.startswith(fa + "/"):
                return True
    return False


def group_by_fork(wus: list[dict]) -> dict[str | None, list[dict]]:
    """按 execution_mode 和 parallel_group 分组。

    - execution_mode=fork → 由 parallel_group 决定并行组（同组 WU 一起分派）
    - execution_mode=inline/serial → 各自串行组（key=None）
    - 组内验证：files_allowed 互不重叠
    """
    fork_groups: dict[str, list[dict]] = {}   # parallel_group → WUs
    serial_wus: list[dict] = []

    for wu in wus:
        if wu.get("status") != "pending":
            continue

        # 检查依赖：depends_on 中的 WU 必须全部 integrated
        deps = wu.get("depends_on", [])
        if deps:
            dep_statuses = {
                d["id"]: d["status"]
                for d in wus
                if d["id"] in deps
            }
            if not all(s == "integrated" for s in dep_statuses.values()):
                continue

        exec_mode = wu.get("execution_mode", "inline")

        if exec_mode == "fork":
            pg = wu.get("parallel_group")
            if not pg:
                print(f"  [WARN] {wu['id']}: execution_mode=fork 但 parallel_group 为空，降级为 serial")
                serial_wus.append(wu)
                continue
            if pg not in fork_groups:
                fork_groups[pg] = []
            fork_groups[pg].append(wu)
        else:
            # inline 或 serial → 串行
            serial_wus.append(wu)

    # 验证 fork 组内 files_allowed 不重叠
    validated: dict[str | None, list[dict]] = {}
    for pg, members in fork_groups.items():
        ok = []
        for wu in members:
            wu_files = wu.get("files_allowed", [])
            if not wu_files:
                continue
            if not any(
                _files_overlap(wu_files, o.get("files_allowed", []))
                for o in ok
            ):
                ok.append(wu)
        if ok:
            validated[pg] = ok

    # 串行 WU 放入 None 组
    if serial_wus:
        validated[None] = serial_wus

    return validated


def find_parallel_wus(wus: list[dict]) -> list[dict]:
    """兼容旧接口：返回第一个可并行组的 WU 列表。"""
    groups = group_by_fork(wus)
    # 优先返回命名组（显式并行），否则取第一个 null 组
    for group, members in groups.items():
        if group is not None and len(members) >= 2:
            return members
    for group, members in groups.items():
        if group is None:
            return members[:1]  # 只返回一个串行 WU
    return []


# ── Prompt 生成 ─────────────────────────────────────────

def _read_project_context(root: Path) -> str:
    """读项目 Prompt.md 前 80 行作为 worker 上下文。"""
    prompt_paths = [
        root / "Prompt.md",
        root / ".claude" / "DEEPSHIP" / "Prompt.md",
    ]
    for pp in prompt_paths:
        if pp.exists():
            lines = pp.read_text(encoding="utf-8").splitlines()[:80]
            return "\n".join(lines)
    return "（未找到 Prompt.md —— 请根据代码库现状自行判断）"


def generate_wu_prompt(wu: dict, root: Path) -> str:
    context = _read_project_context(root)
    files = ", ".join(wu.get("files_allowed", []))
    tests = "\n".join(f"- {t}" for t in wu.get("acceptance_tests", [])) or "（未指定）"

    prompt = PROMPT_TEMPLATE
    subs = {
        "{wu_id}": wu["id"],
        "{goal}": wu.get("goal", ""),
        "{scope}": wu.get("scope", "（未指定）"),
        "{files_allowed}": files,
        "{acceptance_tests}": tests,
        "{project_context}": context,
    }
    for key, value in subs.items():
        prompt = prompt.replace(key, value)
    return prompt


# ── Worktree 管理 ───────────────────────────────────────

def _get_worktree_path(project_root: Path, wu_id: str) -> Path:
    """返回 worktree 的绝对路径：<project_root>/../.deepship-worktrees/<wu_id>/"""
    return (project_root.parent / WORKTREE_PARENT / wu_id).resolve()


def create_worktree(project_root: Path, wu_id: str) -> Path | None:
    """为指定 WU 创建 git worktree。返回 worktree 路径，失败返回 None。"""
    wt_path = _get_worktree_path(project_root, wu_id)

    # 如果已存在，先清理
    if wt_path.exists():
        print(f"  [WORKTREE] 清理已有 worktree: {wt_path}")
        _remove_worktree(wt_path)

    wt_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        result = subprocess.run(
            ["git", "-C", str(project_root), "worktree", "add", "--detach", str(wt_path), "HEAD"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            print(f"  [WORKTREE] 创建失败 {wu_id}: {result.stderr.strip()}")
            return None
        print(f"  [WORKTREE] 创建完成: {wt_path}")
        return wt_path
    except subprocess.TimeoutExpired:
        print(f"  [WORKTREE] 超时 {wu_id}")
        return None


def _remove_worktree(wt_path: Path) -> bool:
    """清理 worktree。"""
    try:
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(wt_path)],
            capture_output=True, text=True, timeout=15,
        )
        return True
    except Exception:
        return False


def setup_run_dir(wt_path: Path, wu_id: str) -> Path:
    """在 worktree 中创建 .deepship/runs/<wu_id>/ 目录。"""
    run_dir = wt_path / DEEPSHIP_DIR / RUNS_DIR / wu_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def cleanup_worktrees(project_root: Path, wu_ids: list[str]) -> None:
    """清理指定 WU 的 worktree。"""
    for wu_id in wu_ids:
        wt_path = _get_worktree_path(project_root, wu_id)
        if wt_path.exists():
            _remove_worktree(wt_path)
            print(f"  [CLEANUP] 已删除 worktree: {wu_id}")


# ── 终端启动 ────────────────────────────────────────────

def _check_wt_available() -> bool:
    try:
        result = subprocess.run(
            ["wt.exe", "--version"],
            capture_output=True, text=True, timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _build_launch_command(
    wu_id: str,
    session_id: str,
    wt_path: Path,
    prompt_file: Path,
) -> list[str]:
    """构建 wt.exe 命令：打开新标签页，在 worktree 目录运行 claude -p。"""
    ps_script = PS_LAUNCHER.format(
        prompt_file=str(prompt_file).replace("\\", "\\\\"),
        extra_flags=(
            f"--name {wu_id} --session-id {session_id} "
            f"--permission-mode auto "
            f"--allowedTools \"{ALLOWED_TOOLS}\" "
            f"--model sonnet "
            f"--no-session-persistence"
        ),
    )
    return [
        "wt.exe", "--title", wu_id,
        "-d", str(wt_path),
        "powershell", "-Command", ps_script,
    ]


def spawn_terminal(
    wu_id: str,
    wt_path: Path,
    prompt: str,
    project_root: Path,
) -> subprocess.Popen | None:
    """在 Windows Terminal 新标签页中启动 Claude Code，工作目录指向 worktree。"""
    if not _validate_wu_id(wu_id):
        print(f"  [REJECTED] {wu_id} —— WU ID 格式不合法（需匹配 {WU_ID_PATTERN}）")
        return None

    session_id = str(uuid.uuid4())

    # 将 prompt 写入 worktree 的 runs 目录
    run_dir = setup_run_dir(wt_path, wu_id)
    prompt_file = run_dir / "prompt.md"
    prompt_file.write_text(prompt, encoding="utf-8")

    cmd = _build_launch_command(wu_id, session_id, wt_path, prompt_file)

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"  [SPAWNED] {wu_id}  session={session_id[:8]}...  worktree={wt_path}")
        return proc
    except FileNotFoundError:
        print(f"  [FAILED] {wu_id} —— wt.exe 未找到，是否安装了 Windows Terminal？")
        return None


# ── 结果轮询 ────────────────────────────────────────────

def _read_result(wt_path: Path, wu_id: str) -> dict | None:
    """读取 worktree 中的 result.json。"""
    result_file = wt_path / DEEPSHIP_DIR / RUNS_DIR / wu_id / "result.json"
    if not result_file.exists():
        return None
    try:
        return json.loads(result_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def monitor(
    wu_ids: list[str],
    worktree_paths: dict[str, Path],
    interval: float = POLL_INTERVAL,
    timeout: float | None = None,
) -> dict[str, dict]:
    """轮询各 worktree 的 result.json，直到全部收集或超时。返回 {wu_id: result}。"""
    import time as _time

    if not wu_ids:
        return {}

    terminal_statuses = {"done", "failed"}
    results: dict[str, dict] = {}
    start_time = _time.monotonic()

    wt_map = {wid: _get_result_path(worktree_paths[wid], wid) for wid in wu_ids}
    print(f"\n[MONITOR] 等待 {len(wu_ids)} 个 worker: {', '.join(wu_ids)}")
    if timeout:
        print(f"[MONITOR] 超时: {timeout}s, 轮询间隔: {interval}s\n")
    else:
        print(f"[MONITOR] 轮询间隔: {interval}s（Ctrl+C 停止）\n")

    try:
        while len(results) < len(wu_ids):
            if timeout and (_time.monotonic() - start_time) > timeout:
                elapsed = int(_time.monotonic() - start_time)
                print(f"\n[MONITOR] 超时 ({elapsed}s)，停止等待。")
                break

            _time.sleep(interval)

            for wu_id in wu_ids:
                if wu_id in results:
                    continue
                result = _read_result(worktree_paths[wu_id], wu_id)
                if result and result.get("status") in terminal_statuses:
                    results[wu_id] = result
                    icon = "OK" if result.get("status") == "done" else "!!"
                    print(f"  [{icon}] {wu_id} → {result.get('status')}  "
                          f"changed_files={result.get('changed_files', [])}")

            pending = [wid for wid in wu_ids if wid not in results]
            if pending:
                print(f"  [WAITING] 剩余 {len(pending)}: {', '.join(pending)}")

    except KeyboardInterrupt:
        print("\n[MONITOR] 已中断。worker 可能仍在终端中运行。")

    return results


def _get_result_path(wt_path: Path, wu_id: str) -> Path:
    return wt_path / DEEPSHIP_DIR / RUNS_DIR / wu_id / "result.json"


# ── 汇总报告 ────────────────────────────────────────────

def print_summary(results: dict[str, dict], wus: list[dict]) -> None:
    wu_map = {w["id"]: w for w in wus}
    done_count = sum(1 for r in results.values() if r.get("status") == "done")
    fail_count = sum(1 for r in results.values() if r.get("status") == "failed")

    print("\n" + "=" * 60)
    print("  分派汇总")
    print("=" * 60)

    for wu_id, result in results.items():
        wu = wu_map.get(wu_id, {})
        icon = "DONE" if result.get("status") == "done" else "FAIL"
        print(f"  [{icon}] {wu_id}: {wu.get('goal', '?')}")
        print(f"        修改文件: {result.get('changed_files', [])}")
        print(f"        测试: {result.get('tests_run', [])}")
        if result.get("risks"):
            print(f"        风险: {result.get('risks')}")

    not_collected = [w["id"] for w in wus
                     if w["id"] not in results and w.get("status") == "pending"]
    if not_collected:
        print(f"\n  未收集: {not_collected}（worker 可能仍在运行）")

    print(f"\n  完成: {done_count}, 失败: {fail_count}")
    print(f"  下一步: python adapters/parallel/collector.py 验证结果")
    print("=" * 60)


# ── 主入口 ──────────────────────────────────────────────

def dispatch(
    project_root: Path | None = None,
    mode: str = "auto",
    wu_filter: list[str] | None = None,
    no_monitor: bool = False,
    timeout: float | None = None,
    cleanup: bool = False,
) -> dict[str, dict]:
    """主入口：加载 WU → 分组 → 创建 worktree → 启动终端 → 监控 → 汇总。

    返回 {wu_id: result_dict}。
    """
    root = project_root or find_deepship_root()
    if root is None:
        print("[ERROR] 未找到 .deepship/ 目录。请在 DEEPSHIP 项目根目录下运行。")
        sys.exit(1)

    print(f"[DISPATCH] 项目根目录: {root}")
    print(f"[DISPATCH] 模式: {mode}")

    if not _check_wt_available():
        print("[ERROR] 需要 Windows Terminal (wt.exe)，但未找到。")
        sys.exit(1)

    # 加载并筛选
    all_wus = load_work_units(root)
    if not all_wus:
        print("[ERROR] 没有 work unit。请先执行 PLAN_STEP。")
        sys.exit(1)

    if wu_filter:
        for wid in wu_filter:
            if not _validate_wu_id(wid):
                print(f"[ERROR] WU ID 不合法: {wid}（需匹配 {WU_ID_PATTERN}）")
                sys.exit(1)
        wus = [w for w in all_wus if w["id"] in wu_filter]
        print(f"[DISPATCH] 筛选 {len(wus)} 个 WU: {[w['id'] for w in wus]}")
    else:
        groups = group_by_fork(all_wus)
        if not groups:
            print("[DISPATCH] 无可分派 WU。")
            print(f"          条件: status=pending, depends_on 已满足")
            pending = [w["id"] for w in all_wus if w.get("status") == "pending"]
            print(f"          当前 pending: {pending}")
            return {}

        # 选择一个组来执行：优先命名并行组，否则第一个串行组
        for group_name, members in groups.items():
            if group_name is not None and len(members) >= 2:
                wus = members
                print(f"[DISPATCH] Fork 组 '{group_name}': {len(wus)} 个 WU 并行")
                break
        else:
            # 取第一个串行组（只取一个 WU）
            for group_name, members in groups.items():
                if group_name is None and members:
                    wus = members[:1]
                    print(f"[DISPATCH] 串行: 1 个 WU")
                    break
                elif group_name is not None and members:
                    wus = members
                    print(f"[DISPATCH] Fork 组 '{group_name}': {len(wus)} 个 WU 并行")
                    break
            else:
                wus = []

        if not wus:
            print("[DISPATCH] 无可分派 WU。")
            return {}

    print(f"[DISPATCH] {len(wus)} 个 WU:")
    for wu in wus:
        pg = wu.get("parallel_group") or "—"
        files = ", ".join(wu.get("files_allowed", []))
        print(f"  - {wu['id']}  group={pg}  [{files}]")

    # 创建 worktree + 生成 prompt + 启动终端
    print(f"\n[DISPATCH] 创建 worktree 并启动终端...")
    processes: dict[str, subprocess.Popen] = {}
    worktree_paths: dict[str, Path] = {}

    for wu in wus:
        wu_id = wu["id"]

        # 1. 创建 worktree
        wt_path = create_worktree(root, wu_id)
        if wt_path is None:
            print(f"  [SKIP] {wu_id} —— worktree 创建失败")
            continue
        worktree_paths[wu_id] = wt_path

        # 2. 生成 worker prompt
        prompt = generate_wu_prompt(wu, root)

        # 3. 启动终端
        proc = spawn_terminal(wu_id, wt_path, prompt, root)
        if proc:
            processes[wu_id] = proc

    if not processes:
        print("[ERROR] 没有终端启动成功。")
        return {}

    wu_ids = list(processes.keys())

    if no_monitor:
        print(f"\n[DISPATCH] --no-monitor: {len(wu_ids)} 个终端已启动，退出。")
        print(f"           各 worktree 的 prompt 和 result 在:")
        for wid in wu_ids:
            print(f"             {worktree_paths[wid] / DEEPSHIP_DIR / RUNS_DIR / wid}")
        print(f"           收集结果: python adapters/parallel/collector.py")
        return {}

    results = monitor(wu_ids, worktree_paths, timeout=timeout)
    print_summary(results, all_wus)

    if cleanup:
        cleanup_worktrees(root, wu_ids)

    return results


# ── 状态检查 ────────────────────────────────────────────

def check_status(project_root: Path | None = None) -> None:
    root = project_root or find_deepship_root()
    if root is None:
        print("[ERROR] 未找到 .deepship/ 目录。")
        sys.exit(1)

    all_wus = load_work_units(root)
    if not all_wus:
        print("没有 work unit。")
        return

    counts: dict[str, int] = {}
    for w in all_wus:
        s = w.get("status", "pending")
        counts[s] = counts.get(s, 0) + 1

    print(f"Work Unit 状态 ({root}):")
    for status in ["pending", "in_progress", "done", "integrated", "blocked", "failed"]:
        c = counts.get(status, 0)
        if c > 0:
            bar = "█" * c
            print(f"  {status:14s} {c:2d}  {bar}")

    print(f"\n  共 {len(all_wus)} 个 WU")
    groups = group_by_fork(all_wus)
    if groups:
        print(f"  可分派组:")
        for group_name, members in groups.items():
            label = f"fork '{group_name}'" if group_name else "serial"
            ids = [w["id"] for w in members]
            print(f"    {label}: {ids}")
        print(f"  运行: python adapters/parallel/dispatcher.py --mode auto")


# ── CLI ─────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="DEEPSHIP Parallel Terminal Dispatcher v0.1",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
示例:
  python adapters/parallel/dispatcher.py --mode auto
  python adapters/parallel/dispatcher.py --mode check
  python adapters/parallel/dispatcher.py --wu WU-001,WU-002
  python adapters/parallel/dispatcher.py --mode auto --no-monitor
  python adapters/parallel/dispatcher.py --mode auto --timeout 600 --cleanup
        """,
    )
    parser.add_argument(
        "--mode", "-m",
        choices=["auto", "check"],
        default="auto",
        help="auto: 创建 worktree + 启动终端; check: 仅查看状态",
    )
    parser.add_argument(
        "--wu",
        type=str,
        help="逗号分隔的 WU ID（默认：自动检测可并行 WU）",
    )
    parser.add_argument(
        "--no-monitor",
        action="store_true",
        help="启动终端后不监控，直接退出",
    )
    parser.add_argument(
        "--project-root", "-d",
        type=str,
        help="项目根目录（默认：从当前目录自动检测）",
    )
    parser.add_argument(
        "--interval", "-i",
        type=float,
        default=POLL_INTERVAL,
        help=f"轮询间隔，秒（默认: {POLL_INTERVAL}）",
    )
    parser.add_argument(
        "--timeout", "-t",
        type=float,
        default=None,
        help="最长等待时间，秒（默认: 不限）",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="监控完成后自动清理 worktree",
    )

    args = parser.parse_args()

    root = Path(args.project_root) if args.project_root else None
    wu_filter = args.wu.split(",") if args.wu else None

    if args.mode == "check":
        check_status(root)
    else:
        dispatch(
            project_root=root,
            mode=args.mode,
            wu_filter=wu_filter,
            no_monitor=args.no_monitor,
            timeout=args.timeout,
            cleanup=args.cleanup,
        )


if __name__ == "__main__":
    main()
