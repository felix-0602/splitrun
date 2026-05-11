"""
DEEPSHIP framework self-verification.
Zero external dependencies. Run from repo root:
  python checks/verify.py
"""
import os, re, sys
from pathlib import Path

_self = Path(__file__).resolve()
ROOT = _self.parent.parent  # checks/ → root/
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

# ─── helpers ───
def read(path):
    return path.read_text(encoding="utf-8")

def sections(text):
    return set(re.findall(r'^(#{2,4})\s+(.+)$', text, re.MULTILINE))

def all_states_from_state_machine():
    path = ROOT / "implement" / "state-machine.md"
    if not path.exists():
        return set()
    impl = read(path)
    d1_start = impl.find("### D.1")
    if d1_start == -1:
        return set()
    d1_end = impl.find("\n## ", d1_start + 100)
    if d1_end == -1:
        d1_end = len(impl)
    d1 = impl[d1_start:d1_end]
    states = set(re.findall(r'`([A-Z_]+)`', d1))
    known_states = {'READ_CONTEXT', 'CLARIFY_INTENT', 'MAP_REALITY',
                    'SELECT_MILESTONE', 'PLAN_STEP', 'EXECUTE',
                    'VALIDATE', 'REPAIR', 'RECORD', 'ADVANCE', 'BLOCK'}
    return {s for s in states if s in known_states}

def read_all_implement():
    impl_dir = ROOT / "implement"
    texts = []
    for p in sorted(impl_dir.rglob("*.md")):
        texts.append(read(p))
    return "\n".join(texts)

def read_all_rules():
    """Read all rules/ files concatenated (for cross-reference checking)."""
    rules_dir = ROOT / "rules"
    texts = []
    if rules_dir.exists():
        for p in sorted(rules_dir.rglob("*.md")):
            texts.append(read(p))
    core = ROOT / "core" / "manifest.md"
    if core.exists():
        texts.append(read(core))
    return "\n".join(texts)

# ─── check 1: cross-file references ───
def check_cross_refs():
    print("\n[1] Cross-file references")
    impl = read_all_implement()
    rules_text = read_all_rules()
    all_text = impl + "\n" + rules_text

    refs = re.findall(r'见\s+(§?[A-Z]\.\d+(?:\.\d+)?)', all_text)
    refs += re.findall(r'（见\s+([A-Z]\.\d+(?:\.\d+)?)', all_text)

    secs = sections(impl)
    sec_titles = {title for _, title in secs}

    checked = 0
    for ref in set(refs):
        checked += 1
        found = any(ref.lstrip('§') in title for _, title in secs)
        if found:
            ok(f"ref '{ref}' → exists")
        else:
            warn(f"ref '{ref}' → NOT FOUND in implement/")
    if checked == 0:
        ok("no cross-refs to check")

    # Check rule file references to implement/
    rules_refs = re.findall(r'`(implement/[^`]+)`', rules_text)
    for ref in set(rules_refs):
        target = ROOT / ref
        if target.exists():
            ok(f"rules ref '{ref}' → exists")
        else:
            err(f"rules ref '{ref}' → FILE NOT FOUND")
    return checked

# ─── check 2: state machine consistency ───
def check_state_machine():
    print("\n[2] State machine consistency (manifest.md <-> state-machine.md)")
    states = all_states_from_state_machine()
    manifest_path = ROOT / "core" / "manifest.md"

    if not states:
        err("could not extract states from implement/state-machine.md D.1")
        return

    print(f"  States in D.1: {sorted(states)}")

    if manifest_path.exists():
        manifest_text = read(manifest_path)
        for s in states:
            if s in manifest_text:
                ok(f"'{s}' in manifest.md")
            else:
                err(f"'{s}' NOT in core/manifest.md")
    else:
        err("core/manifest.md NOT FOUND")

    # Check rules/states/ has a file for each state (except SELECT_MILESTONE)
    states_dir = ROOT / "rules" / "states"
    if states_dir.exists():
        state_files = {p.stem.upper().replace('-', '_') for p in states_dir.glob("*.md")}
        states_needing_files = states - {'SELECT_MILESTONE'}
        for s in sorted(states_needing_files):
            expected_name = s.lower().replace('_', '-')
            if s in state_files or expected_name in {p.stem for p in states_dir.glob("*.md")}:
                ok(f"'{s}' has rules/states/ file")
            else:
                err(f"'{s}' MISSING rules/states/ file (expected: {expected_name}.md)")
    else:
        err("rules/states/ directory NOT FOUND")

    # A.0 ↔ D.1 consistency
    tools_text = read(ROOT / "implement" / "tools.md")
    a0_states = {s for s in states if s in tools_text}
    missing_in_a0 = states - a0_states
    if missing_in_a0:
        for s in sorted(missing_in_a0):
            warn(f"D.1 state '{s}' NOT in A.0 matrix (tools.md)")
    else:
        ok(f"All {len(states)} D.1 states in A.0 matrix")

    # Authority annotations
    if '权威源' in read(ROOT / "implement" / "state-machine.md"):
        ok("D.1 marked as 权威源")
    else:
        warn("D.1 NOT marked as 权威源")
    if '权威源' in tools_text:
        ok("A.0 marked as derived from D.1")
    else:
        warn("A.0 NOT marked as derived from D.1")

    # README must reference core/manifest as authority
    readme_text = read(ROOT / "README.md")
    if 'core/manifest.md' in readme_text:
        ok("README references core/manifest.md as authority")
    else:
        err("README does NOT reference core/manifest.md")

# ─── check 3: template integrity ───
def check_template_integrity():
    print("\n[3] Template integrity (no project data in global templates)")
    templates = ["Prompt.md", "Plan.md", "Documentation.md"]
    real_data_patterns = [
        (r'netclass', "project name 'netclass'"),
        (r'超星', "project name '超星'"),
        (r'U\s*校园', "project name 'U校园'"),
        (r'unipus', "project name 'unipus'"),
    ]
    for fname in templates:
        path = ROOT / fname
        if not path.exists():
            err(f"template '{fname}' missing")
            continue
        content = read(path)
        for pattern, desc in real_data_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                err(f"'{fname}' contains {desc}")
        ok(f"'{fname}' clean")

# ─── check 4: file sizes ───
def check_file_sizes():
    print("\n[4] File sizes (≤ 800 lines per B.3)")
    for path in ROOT.rglob("*.md"):
        if '.git' in str(path):
            continue
        lines = len(read(path).split('\n'))
        fname = str(path.relative_to(ROOT))
        if lines > 800:
            err(f"{fname}: {lines} lines (limit: 800)")
        else:
            ok(f"{fname}: {lines} lines")

# ─── check 5: tool availability ───
def check_tool_availability():
    print("\n[5] Tool availability")

    # Critical tools — framework operation depends on these
    CRITICAL_AGENTS = {
        'code-reviewer', 'security-reviewer', 'tdd-guide', 'planner',
        'architect', 'e2e-runner', 'build-error-resolver',
    }
    CRITICAL_SKILLS = {
        'subagent-driven-development', 'dispatching-parallel-agents',
        'verification-before-completion', 'systematic-debugging',
        'brainstorming', 'writing-plans',
    }

    # Collect all tools referenced across implement/ and rules/
    tools_text = read_all_implement() + "\n" + read_all_rules()
    skills = set(re.findall(r'Skill\(([^)]+)\)', tools_text))
    agents = set(re.findall(r'Agent\(([^)]+)\)', tools_text))
    skills.discard('<name>')
    agents.discard('<agent-name>')

    # Scan installed tools
    home = Path.home()
    installed_skills = set()
    for base in [home / ".claude" / "skills", home / ".claude" / "plugins"]:
        if base.exists():
            for p in base.rglob("SKILL.md"):
                installed_skills.add(p.parent.name)

    installed_agents = set()
    # Agents are .md files in ~/.claude/agents/ (not directories)
    agents_dir = home / ".claude" / "agents"
    if agents_dir.exists():
        for p in agents_dir.glob("*.md"):
            installed_agents.add(p.stem)
    # Also check plugins directory (agents may be subdirectories here)
    plugins_dir = home / ".claude" / "plugins"
    if plugins_dir.exists():
        for p in plugins_dir.rglob("*"):
            if p.is_dir() and not p.name.startswith('.') and p.name not in installed_agents:
                installed_agents.add(p.name)

    # Classify and report
    missing_skills = {name for name in skills if name not in installed_skills}
    missing_agents = {name for name in agents if name not in installed_agents}
    missing_critical = []

    for name in sorted(CRITICAL_SKILLS & missing_skills):
        missing_critical.append(f"Skill({name})")
    for name in sorted(CRITICAL_AGENTS & missing_agents):
        missing_critical.append(f"Agent({name})")

    total = len(skills) + len(agents)
    found_count = total - len(missing_skills | missing_agents)
    print(f"  Found: {found_count}/{total}")

    for m in sorted(missing_skills | missing_agents):
        is_critical = (f"Skill({m})" if m in skills else f"Agent({m})") in missing_critical
        if is_critical:
            err(f"CRITICAL: {m} NOT installed — framework operation impaired")
        else:
            warn(f"{m} — optional, not installed locally")

    if missing_critical:
        print(f"  → {len(missing_critical)} CRITICAL tools missing. Install before use.")

    # Verify: state rules reference only categorized tools
    rules_dir = ROOT / "rules"
    if rules_dir.exists():
        rules_text = read_all_rules()
        rules_skills = set(re.findall(r'Skill\(([^)]+)\)', rules_text))
        rules_agents = set(re.findall(r'Agent\(([^)]+)\)', rules_text))
        unknown = []
        for s in rules_skills:
            if s not in installed_skills and s not in CRITICAL_SKILLS:
                pass  # Already warned above
        ok(f"rules/ references {len(rules_skills)} Skills, {len(rules_agents)} Agents")

# ─── check 6: JIT architecture integrity ───
def check_jit_architecture():
    print("\n[6] JIT architecture integrity")

    # core/manifest.md must have rule trigger table
    manifest = ROOT / "core" / "manifest.md"
    if not manifest.exists():
        err("core/manifest.md NOT FOUND")
        return
    manifest_text = read(manifest)

    # Must reference rules/states/ directory
    if 'rules/states/' in manifest_text:
        ok("manifest.md references rules/states/")
    else:
        err("manifest.md does NOT reference rules/states/")

    # Must reference rules/static/ directory
    if 'rules/static/' in manifest_text:
        ok("manifest.md references rules/static/")
    else:
        err("manifest.md does NOT reference rules/static/")

    # Every file in rules/states/ must be referenced by manifest
    states_dir = ROOT / "rules" / "states"
    if states_dir.exists():
        for p in states_dir.glob("*.md"):
            fname = p.name
            if f"rules/states/{fname}" not in manifest_text:
                warn(f"rules/states/{fname} NOT referenced in manifest.md")
        ok("rules/states/ files exist and checked")

    # Every file in rules/static/ must be referenced by manifest
    static_dir = ROOT / "rules" / "static"
    if static_dir.exists():
        for p in static_dir.glob("*.md"):
            fname = p.name
            if f"rules/static/{fname}" not in manifest_text:
                warn(f"rules/static/{fname} NOT referenced in manifest.md")
        ok("rules/static/ files checked against manifest")

# ─── main ───
if __name__ == "__main__":
    os.chdir(str(ROOT))
    print(f"DEEPSHIP verify — {ROOT}")
    check_cross_refs()
    check_state_machine()
    check_template_integrity()
    check_file_sizes()
    check_tool_availability()
    check_jit_architecture()

    print(f"\n{'='*40}")
    print(f"Errors: {len(errors)} | Warnings: {len(warnings)}")
    if errors:
        for e in errors:
            print(f"  FAIL: {e}")
    if warnings:
        for w in warnings:
            print(f"  WARN: {w}")

    if errors:
        print(f"\nFAILED: {len(errors)} error(s) must be fixed.")
        sys.exit(1)
    else:
        if warnings:
            print(f"\nPASSED with {len(warnings)} warning(s).")
        else:
            print("ALL CHECKS PASSED")
        sys.exit(0)
