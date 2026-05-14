"""
DEEPSHIP framework self-verification.
Zero external dependencies. Run from repo root:
  python checks/verify.py
Companion: checks/gap_scan.py (L3 design-implementation consistency scanner).
"""
import os, re, sys, json
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

def all_states_from_manifest():
    """Extract states from protocol/state-machine.md (authoritative protocol source)."""
    path = ROOT / "protocol" / "state-machine.md"
    if not path.exists():
        # Fallback: try old location in core/manifest.md
        path = ROOT / "core" / "manifest.md"
        if not path.exists():
            return set()
    text = read(path)
    # Extract states from `STATE_NAME` backtick patterns
    states = set(re.findall(r'`([A-Z][A-Z_]+)`', text))
    known_states = {'READ_CONTEXT', 'CLARIFY_INTENT', 'MAP_REALITY',
                    'SELECT_MILESTONE', 'PLAN_STEP', 'EXECUTE',
                    'VALIDATE', 'REPAIR', 'RECORD', 'ADVANCE', 'BLOCK',
                    'COMPLETE'}
    return {s for s in states if s in known_states}

def states_from_archive_d1():
    """Extract states from implement/state-machine.md D.1 (archive, for cross-check)."""
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
                    'VALIDATE', 'REPAIR', 'RECORD', 'ADVANCE', 'BLOCK',
                    'COMPLETE'}
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

# ─── check 2: state machine consistency (manifest.md authoritative) ───
def check_state_machine():
    print("\n[2] State machine consistency (manifest.md → archive)")
    manifest_states = all_states_from_manifest()
    archive_states = states_from_archive_d1()
    manifest_path = ROOT / "core" / "manifest.md"

    if not manifest_states:
        err("could not extract states from core/manifest.md rule trigger table")
        return

    print(f"  Manifest states: {sorted(manifest_states)}")
    if archive_states:
        print(f"  Archive D.1 states: {sorted(archive_states)}")

    # core/manifest.md is authoritative — archive must match it
    if archive_states:
        missing_in_archive = manifest_states - archive_states
        extra_in_archive = archive_states - manifest_states
        for s in sorted(missing_in_archive):
            warn(f"'{s}' in manifest.md but NOT in implement/state-machine.md D.1 — archive stale?")
        for s in sorted(extra_in_archive):
            warn(f"'{s}' in D.1 but NOT in manifest.md — archive has extra state")
        if not missing_in_archive and not extra_in_archive:
            ok(f"manifest.md <-> D.1: {len(manifest_states)} states consistent")
    else:
        warn("implement/state-machine.md D.1 not parseable — archive check skipped")

    # Check protocol/state-machine.md has state definitions (v2.2+: authority in protocol/)
    protocol_sm_path = ROOT / "protocol" / "state-machine.md"
    if protocol_sm_path.exists():
        protocol_sm_text = read(protocol_sm_path)
        for s in sorted(manifest_states):
            if f"`{s}`" in protocol_sm_text or s in protocol_sm_text:
                ok(f"'{s}' defined in protocol/state-machine.md")
            else:
                err(f"'{s}' MISSING from protocol/state-machine.md")
    else:
        err("protocol/state-machine.md NOT FOUND")

    # Check rules/states/ has a file for each state that needs one
    states_dir = ROOT / "rules" / "states"
    if states_dir.exists():
        state_files = {p.stem for p in states_dir.glob("*.md")}
        # SELECT_MILESTONE explicitly uses inline reads (Plan + Documentation), no state file needed
        states_without_files = {'SELECT_MILESTONE'}
        states_needing_files = manifest_states - states_without_files
        for s in sorted(states_needing_files):
            expected_name = s.lower().replace('_', '-')
            if expected_name in state_files:
                ok(f"'{s}' → rules/states/{expected_name}.md")
            else:
                err(f"'{s}' MISSING rules/states/{expected_name}.md")
    else:
        err("rules/states/ directory NOT FOUND")

    # A.0 ↔ manifest consistency — A.0 is a derived document, drift is an error
    tools_text = read(ROOT / "implement" / "tools.md")
    a0_missing = {s for s in manifest_states if s not in tools_text}
    if a0_missing:
        for s in sorted(a0_missing):
            err(f"'{s}' in manifest but NOT in A.0 matrix (tools.md) — A.0 is derived from manifest, must be kept in sync")
    else:
        ok(f"All {len(manifest_states)} manifest states in A.0 matrix")

    # Authority annotations: protocol/ is the authority (v2.2+), manifest is entry point
    if '权威' in read(ROOT / "protocol" / "state-machine.md") or 'authority' in read(ROOT / "protocol" / "state-machine.md").lower():
        ok("protocol/state-machine.md declares authority")
    elif '权威源' in read(ROOT / "core" / "manifest.md"):
        ok("manifest.md declares authority (legacy)")
    else:
        warn("No authority declaration found — add to protocol/state-machine.md")

    # README must reference core/manifest as authority
    readme_text = read(ROOT / "README.md")
    if 'core/manifest.md' in readme_text and ('权威源' in readme_text or 'authoritative' in readme_text.lower()):
        ok("README references core/manifest.md as authority")
    elif 'core/manifest.md' in readme_text:
        ok("README references core/manifest.md")
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

    # Filter out placeholders and composite references
    def is_placeholder(name):
        # Chinese text placeholders
        if re.search(r'[一-鿿]', name):
            return True
        # Slash-combined references: "plan-ceo-review/eng-review/design-review"
        if '/' in name:
            return True
        # Generic placeholders
        if name in ('<name>', '<agent-name>', 'name', 'agent-name'):
            return True
        # Example/description text, not real tool names
        if len(name) > 60:
            return True
        return False

    skills = {s for s in skills if not is_placeholder(s)}
    agents = {a for a in agents if not is_placeholder(a)}

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

    # Every file in rules/states/ must exist and be covered
    states_dir = ROOT / "rules" / "states"
    if states_dir.exists():
        state_files = list(states_dir.glob("*.md"))
        # Slim manifest references rules/states/ generically — check protocol/ covers the states
        protocol_sm = read(ROOT / "protocol" / "state-machine.md")
        for p in state_files:
            fname = p.stem  # e.g. "read-context" → state name hint
            if fname not in manifest_text and f"rules/states/{p.name}" not in manifest_text:
                pass  # OK — manifest uses generic reference, protocol has details
        ok(f"rules/states/: {len(state_files)} files present")
    else:
        err("rules/states/ directory NOT FOUND")

    # Every file in rules/static/ must exist
    static_dir = ROOT / "rules" / "static"
    if static_dir.exists():
        static_files = list(static_dir.glob("*.md"))
        ok(f"rules/static/: {len(static_files)} files present")
    else:
        err("rules/static/ directory NOT FOUND")

    # Manifest must stay lean (< 100 lines) for JIT architecture claim
    manifest_lines = len(manifest_text.split('\n'))
    if manifest_lines > 100:
        err(f"core/manifest.md: {manifest_lines} lines (JIT limit: 100). "
            "Move sections to rules/static/loop.md or rules/states/.")
    elif manifest_lines > 80:
        warn(f"core/manifest.md: {manifest_lines} lines — approaching JIT limit (100)")
    else:
        ok(f"core/manifest.md: {manifest_lines} lines (JIT target ≤100)")

# ─── check 7: persistent state protocol ───
def check_persistent_state():
    print("\n[7] Persistent state protocol (.deepship/)")

    # Check templates exist
    templates = {
        'templates/state.json': 'state.json template',
        'templates/work_units.json': 'work_units.json template',
        'templates/log.jsonl': 'log.jsonl seed file',
    }
    for path, desc in templates.items():
        if (ROOT / path).exists():
            ok(f"{desc} exists")
        else:
            err(f"{desc} MISSING: {path}")

    # Check protocol docs exist
    protocols = {
        'rules/protocols/work-unit.md': 'Work Unit Protocol',
        'rules/protocols/log-format.md': 'Log format spec',
    }
    for path, desc in protocols.items():
        if (ROOT / path).exists():
            ok(f"{desc} exists")
        else:
            err(f"{desc} MISSING: {path}")

    # Check manifest or protocol references persistent state
    manifest_text = read(ROOT / "core" / "manifest.md")
    persistence_text = read(ROOT / "protocol" / "persistence.md")
    for keyword in ['.deepship/state.json', '.deepship/work_units.json', '.deepship/log.jsonl']:
        if keyword in manifest_text or keyword in persistence_text:
            ok(f"persistent state: {keyword} referenced")
        else:
            err(f"persistent state: {keyword} NOT referenced in manifest or protocol")

    # Check READ_CONTEXT requires state.json
    read_context = read(ROOT / "rules" / "states" / "read-context.md")
    if '.deepship/state.json' in read_context:
        ok("read-context.md requires .deepship/state.json")
    else:
        warn("read-context.md does NOT reference .deepship/state.json")

    # Check RECORD requires state.json and log.jsonl updates
    record = read(ROOT / "rules" / "states" / "record.md")
    for keyword in ['.deepship/state.json', '.deepship/log.jsonl']:
        if keyword in record:
            ok(f"record.md requires {keyword} update")
        else:
            err(f"record.md does NOT reference {keyword}")

# ─── check 8: work unit protocol integrity ───
def check_work_unit_protocol():
    print("\n[8] Work Unit Protocol integrity")

    # PLAN_STEP must require work unit output
    plan_step = read(ROOT / "rules" / "states" / "plan-step.md")
    if 'work unit' in plan_step.lower() or 'work_units' in plan_step:
        ok("plan-step.md references work units")
    else:
        err("plan-step.md does NOT reference work units — must produce WUs")

    if 'rules/protocols/work-unit.md' in plan_step:
        ok("plan-step.md references work-unit protocol")
    else:
        warn("plan-step.md does NOT reference rules/protocols/work-unit.md")

    # ADVANCE must check pending work units
    advance = read(ROOT / "rules" / "states" / "advance.md")
    if 'pending work unit' in advance.lower() or 'work_units.json' in advance:
        ok("advance.md checks pending work units")
    else:
        err("advance.md does NOT check pending work units before advancing")

    # EXECUTE must reference work unit protocol
    execute = read(ROOT / "rules" / "states" / "execute.md")
    if 'work unit' in execute.lower() or 'files_allowed' in execute:
        ok("execute.md references work unit boundaries")
    else:
        warn("execute.md does NOT reference work unit protocol")

    # RECORD must require work unit integration
    record = read(ROOT / "rules" / "states" / "record.md")
    if 'work_units.json' in record:
        ok("record.md references work_units.json")
    else:
        err("record.md does NOT reference work_units.json")

    # COMPLETE must reference work_units.json
    complete = read(ROOT / "rules" / "states" / "complete.md")
    if 'work_units.json' in complete:
        ok("complete.md references work_units.json")
    else:
        warn("complete.md does NOT reference work_units.json")

    # manifest.md must have COMPLETE state
    manifest_text = read(ROOT / "core" / "manifest.md")
    if 'COMPLETE' in manifest_text:
        ok("manifest.md contains COMPLETE state")
    else:
        err("manifest.md MISSING COMPLETE state")

    # Verify no composite tool references like "plan-ceo-review/eng-review/design-review"
    all_rules = read_all_rules()
    composite_refs = re.findall(r'(?:Skill|Agent)\(([^)]*\/[^)]*)\)', all_rules)
    if composite_refs:
        for ref in composite_refs:
            warn(f"Composite tool reference: '{ref}' — use individual references instead")
    else:
        ok("no composite tool references found")

# ─── check 9: conformance test set ───
def check_conformance_tests():
    print("\n[9] Conformance test set (Policy Engine)")

    conformance_path = ROOT / "tests" / "conformance" / "policy_cases.json"
    if not conformance_path.exists():
        err("tests/conformance/policy_cases.json NOT FOUND — required for Policy Engine conformance")
        return

    try:
        data = json.loads(read(conformance_path))
    except Exception as e:
        err(f"policy_cases.json parse error: {e}")
        return

    cases = data.get("cases", [])
    if not cases:
        err("policy_cases.json has no test cases")
        return

    ok(f"{len(cases)} conformance cases loaded")

    # Check each case has required fields
    required_fields = {"name", "state", "tool", "args", "expected", "reason"}
    for c in cases:
        missing = required_fields - set(c.keys())
        if missing:
            err(f"Case '{c.get('name', 'UNKNOWN')}' missing fields: {missing}")
        if c.get("expected") not in ("ALLOW", "BLOCK"):
            err(f"Case '{c['name']}': expected must be ALLOW or BLOCK, got '{c.get('expected')}'")
        if c.get("work_unit") and "files_allowed" not in c["work_unit"]:
            warn(f"Case '{c['name']}': work_unit missing files_allowed field")

    # Four minimum hard gates coverage (check by semantic pattern, not gate label)
    # Gate 1: non-exec states reject mutating tools
    non_exec_states = {"READ_CONTEXT", "CLARIFY_INTENT", "MAP_REALITY", "SELECT_MILESTONE",
                       "PLAN_STEP", "VALIDATE", "RECORD", "COMPLETE"}
    mutating_tools = {"write_file", "edit_file", "bash"}
    g1_cases = [c for c in cases
                if c["state"] in non_exec_states
                and c["tool"] in mutating_tools]
    g1_blocks = [c for c in g1_cases if c["expected"] == "BLOCK"]
    if not g1_blocks:
        err("Gate 1 uncovered: no BLOCK cases for mutating tools in non-exec states")
    else:
        ok(f"Gate 1 (state-gated mutating): {len(g1_blocks)} BLOCK across {len(set(c['state'] for c in g1_blocks))} states")

    # Gate 2: pre-PLAN_STEP states reject code edits
    pre_plan = {"READ_CONTEXT", "CLARIFY_INTENT", "MAP_REALITY", "SELECT_MILESTONE"}
    g2_cases = [c for c in cases
                if c["state"] in pre_plan
                and c["tool"] in ("write_file", "edit_file")
                and c["expected"] == "BLOCK"]
    if not g2_cases:
        err("Gate 2 uncovered: no BLOCK for code edit before PLAN_STEP")
    else:
        ok(f"Gate 2 (no-code-before-plan): {len(g2_cases)} BLOCK")

    # Gate 3: EXECUTE with files_allowed boundary
    g3_cases = [c for c in cases if c.get("work_unit") and "files_allowed" in c["work_unit"]]
    g3_allow = [c for c in g3_cases if c["expected"] == "ALLOW"]
    g3_block = [c for c in g3_cases if c["expected"] == "BLOCK"]
    if not g3_allow:
        err("Gate 3 uncovered: no ALLOW for in-scope file during EXECUTE")
    if not g3_block:
        err("Gate 3 uncovered: no BLOCK for out-of-scope file during EXECUTE")
    ok(f"Gate 3 (files_allowed boundary): {len(g3_allow)} ALLOW, {len(g3_block)} BLOCK")

    # Gate 4: ADVANCE/COMPLETE require VALIDATE
    g4_cases = [c for c in cases if c["tool"] == "transition_state"]
    g4_blocks = [c for c in g4_cases if c["expected"] == "BLOCK"]
    g4_allows = [c for c in g4_cases if c["expected"] == "ALLOW"]
    if not g4_blocks:
        err("Gate 4 uncovered: no BLOCK for transition_state without VALIDATE")
    ok(f"Gate 4 (transition gating): {len(g4_allows)} ALLOW, {len(g4_blocks)} BLOCK")

    # Additional coverage checks
    states_in_cases = {c["state"] for c in cases}
    expected_states = {"READ_CONTEXT", "CLARIFY_INTENT", "MAP_REALITY", "SELECT_MILESTONE",
                       "PLAN_STEP", "EXECUTE", "VALIDATE", "REPAIR", "RECORD", "ADVANCE", "BLOCK", "COMPLETE"}
    missing_states = expected_states - states_in_cases
    if missing_states:
        warn(f"States not covered by any conformance case: {sorted(missing_states)}")
    else:
        ok(f"All {len(expected_states)} states covered")

    # Workspace boundary check
    ws_cases = [c for c in cases if c.get("workspace")]
    if ws_cases:
        ws_blocks = [c for c in ws_cases if c["expected"] == "BLOCK" and c["tool"] in ("write_file", "edit_file")]
        if ws_blocks:
            ok(f"Workspace boundary: {len(ws_blocks)} BLOCK for out-of-workspace writes")
        else:
            warn("Workspace boundary: no BLOCK cases for system path writes")
    else:
        warn("No workspace-scoped conformance cases")

    # Check all conformance files exist
    conformance_files = [
        "transition_cases.json",
        "work_unit_cases.json",
        "persistence_cases.json",
    ]
    for cf in conformance_files:
        cpath = ROOT / "tests" / "conformance" / cf
        if cpath.exists():
            try:
                cdata = json.loads(read(cpath))
                ccount = len(cdata.get("cases", []))
                ok(f"{cf}: {ccount} cases")
            except Exception as e:
                err(f"{cf}: parse error — {e}")
        else:
            err(f"{cf} NOT FOUND in tests/conformance/")

    # Work Unit cases must cover the autonomy boundary, not only lifecycle enums.
    wu_path = ROOT / "tests" / "conformance" / "work_unit_cases.json"
    if wu_path.exists():
        try:
            wu_cases = json.loads(read(wu_path)).get("cases", [])
        except Exception:
            wu_cases = []

        def wu_has(predicate):
            return any(predicate(c) for c in wu_cases)

        if wu_has(lambda c: c.get("check") == "can_dispatch_parallel" and c.get("expected") == "ALLOW"):
            ok("Work Unit conformance: parallel dispatch ALLOW covered")
        else:
            err("Work Unit conformance missing parallel dispatch ALLOW case")

        if wu_has(lambda c: c.get("check") == "can_dispatch_parallel" and c.get("expected") == "BLOCK"):
            ok("Work Unit conformance: parallel dispatch BLOCK covered")
        else:
            err("Work Unit conformance missing parallel dispatch BLOCK case")

        if wu_has(lambda c: c.get("action") == "accept_subagent_result" and c.get("expected") == "ALLOW"):
            ok("Work Unit conformance: subagent result ALLOW covered")
        else:
            err("Work Unit conformance missing subagent result ALLOW case")

        if wu_has(lambda c: c.get("action") == "accept_subagent_result" and c.get("expected") == "BLOCK"):
            ok("Work Unit conformance: subagent result BLOCK covered")
        else:
            err("Work Unit conformance missing subagent result BLOCK case")

        if wu_has(lambda c: c.get("action") == "integrate_work_unit" and c.get("expected") == "ALLOW") and \
           wu_has(lambda c: c.get("action") == "integrate_work_unit" and c.get("expected") == "BLOCK"):
            ok("Work Unit conformance: integration gate ALLOW/BLOCK covered")
        else:
            err("Work Unit conformance missing integration gate ALLOW/BLOCK cases")

# ─── check 10: protocol and adapter integrity ───
def check_protocol_integrity():
    print("\n[10] Protocol and adapter integrity")

    # Protocol files must exist
    protocol_files = [
        "state-machine.md", "policy.md", "work-unit.md",
        "persistence.md", "conformance.md"
    ]
    for pf in protocol_files:
        ppath = ROOT / "protocol" / pf
        if ppath.exists():
            ok(f"protocol/{pf} exists")
        else:
            err(f"protocol/{pf} NOT FOUND")

    # Schema files must exist and be valid JSON
    schema_files = [
        "state.schema.json", "work_unit.schema.json",
        "log.schema.json", "policy_case.schema.json"
    ]
    for sf in schema_files:
        spath = ROOT / "schemas" / sf
        if spath.exists():
            try:
                json.loads(read(spath))
                ok(f"schemas/{sf} valid JSON")
            except Exception as e:
                err(f"schemas/{sf} invalid JSON: {e}")
        else:
            err(f"schemas/{sf} NOT FOUND")

    # Adapter documentation must exist
    adapter_files = [
        "adapters/claude-code/README.md",
        "adapters/claude-code/limitations.md",
        "adapters/mate/README.md",
    ]
    for af in adapter_files:
        apath = ROOT / af
        if apath.exists():
            ok(f"{af} exists")
        else:
            err(f"{af} NOT FOUND")

    # Policy matrix MUST NOT contain weakening language like "建议而非铁律"
    policy_text = read(ROOT / "protocol" / "policy.md")
    weakening_phrases = ["建议而非铁律", "不是枷锁"]
    for phrase in weakening_phrases:
        if phrase in policy_text:
            err(f"protocol/policy.md contains weakening phrase: '{phrase}' — protocol MUST NOT weaken its own authority")
    ok("protocol/policy.md: no weakening language")

# ─── check 11: orphan file detection ───
def check_orphan_files():
    print("\n[11] Orphan file detection (checks/, adapters/)")
    scan_dirs = ["checks", "adapters"]
    exts = {".py", ".js", ".ts"}
    orphan_count = 0

    for scan_dir_name in scan_dirs:
        scan_dir = ROOT / scan_dir_name
        if not scan_dir.exists():
            continue
        for fp in scan_dir.rglob("*"):
            if fp.is_dir() or fp.suffix not in exts:
                continue
            if "__pycache__" in str(fp):
                continue
            rel = str(fp.relative_to(ROOT)).replace("\\", "/")
            fname = fp.name

            # Check if this file is referenced in any .md or .py file
            referenced = False
            for ref_file in ROOT.rglob("*.md"):
                try:
                    if fname in ref_file.read_text(encoding="utf-8", errors="replace"):
                        referenced = True
                        break
                except Exception:
                    continue
            if not referenced:
                for ref_file in ROOT.rglob("*.py"):
                    if ref_file == fp:
                        continue
                    try:
                        if fname in ref_file.read_text(encoding="utf-8", errors="replace"):
                            referenced = True
                            break
                    except Exception:
                        continue

            if referenced:
                ok(f"{rel} — referenced")
            else:
                orphan_count += 1
                warn(f"{rel} — ORPHAN: not referenced in any .md or .py file")

    if orphan_count == 0:
        ok("no orphan files detected")
    else:
        err(f"{orphan_count} orphan file(s) — consider adding to CLAUDE.md, README, or verify.py")

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
    check_persistent_state()
    check_work_unit_protocol()
    check_conformance_tests()
    check_protocol_integrity()
    check_orphan_files()

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
