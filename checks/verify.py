"""
DEEPSHIP self-verification.
Zero external dependencies. Run: python checks/verify.py
"""
import os, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
errors = []

def err(msg):
    errors.append(msg)
    print(f"  FAIL: {msg}")

def ok(msg):
    print(f"  OK: {msg}")

# ─── helpers ───
def read(path):
    return path.read_text(encoding="utf-8")

def sections(text):
    """Return set of section headings (## X, ### X.Y, #### X.Y.Z)."""
    return set(re.findall(r'^(#{2,4})\s+(.+)$', text, re.MULTILINE))

def all_states_from_state_machine():
    """Extract state names from implement/state-machine.md D.1 table."""
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
    """Read all implement/ files concatenated (for cross-reference checking)."""
    impl_dir = ROOT / "implement"
    texts = []
    for path in sorted(impl_dir.rglob("*.md")):
        texts.append(read(path))
    return "\n".join(texts)

# ─── check 1: cross-file references ───
def check_cross_refs():
    print("\n[1] Cross-file references")
    impl = read_all_implement()
    refs = re.findall(r'见\s+(§?[A-Z]\.\d+(?:\.\d+)?)', impl)
    refs += re.findall(r'（见\s+([A-Z]\.\d+(?:\.\d+)?)', impl)

    secs = sections(impl)
    sec_titles = {title for _, title in secs}

    checked = 0
    for ref in set(refs):
        checked += 1
        found = False
        for _, title in secs:
            if ref.lstrip('§') in title:
                found = True
                break
        if not found:
            pattern = ref.lstrip('§')
            if any(pattern in title for _, title in secs):
                found = True
        if found:
            ok(f"ref '{ref}' → exists")
        else:
            err(f"ref '{ref}' → NOT FOUND in implement/")
    if checked == 0:
        ok("no cross-refs to check")
    return checked

# ─── check 2: state machine consistency ───
def check_state_machine():
    print("\n[2] State machine consistency (README vs state-machine.md D.1)")
    states = all_states_from_state_machine()
    readme_text = read(ROOT / "README.md")

    if not states:
        err("could not extract states from implement/state-machine.md D.1")
        return

    print(f"  States in D.1: {sorted(states)}")

    # Core flow states that should appear in README
    core_states = {'READ_CONTEXT', 'MAP_REALITY', 'SELECT_MILESTONE',
                   'PLAN_STEP', 'EXECUTE', 'VALIDATE', 'RECORD',
                   'ADVANCE', 'REPAIR', 'BLOCK'}
    # CLARIFY_INTENT is optional
    optional = {'CLARIFY_INTENT'}

    for s in core_states:
        if s not in states:
            err(f"core state '{s}' not found in D.1")

    for s in states - optional:
        if s in ('READ_CONTEXT', 'MAP_REALITY', 'SELECT_MILESTONE',
                  'PLAN_STEP', 'EXECUTE', 'VALIDATE', 'RECORD',
                  'ADVANCE', 'REPAIR', 'BLOCK', 'CLARIFY_INTENT'):
            continue
        # Unknown state
        pass  # could be other constants, skip

    # Check README mentions the core states
    for s in core_states - {'ADVANCE', 'REPAIR', 'BLOCK'}:
        if s not in readme_text:
            err(f"'{s}' not mentioned in README core flow")
        else:
            ok(f"'{s}' in README")

    # CLARIFY_INTENT should also be in README (was fixed earlier)
    if 'CLARIFY_INTENT' in readme_text:
        ok("CLARIFY_INTENT in README")
    else:
        err("CLARIFY_INTENT NOT in README")

# ─── check 3: template integrity ───
def check_template_integrity():
    print("\n[3] Template integrity (no project data in global templates)")
    # These files should be templates, not contain real project data
    templates = ["Prompt.md", "Plan.md", "Documentation.md"]

    # Patterns that suggest real project data (not template placeholders)
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
        if '.git' in str(path) or 'projects' in str(path):
            continue
        lines = len(read(path).split('\n'))
        fname = str(path.relative_to(ROOT))
        if lines > 800:
            err(f"{fname}: {lines} lines (limit: 800)")
        else:
            ok(f"{fname}: {lines} lines")

# ─── main ───
if __name__ == "__main__":
    os.chdir(str(ROOT))
    print(f"DEEPSHIP verify — {ROOT}")
    check_cross_refs()
    check_state_machine()
    check_template_integrity()
    check_file_sizes()

    print(f"\n{'='*40}")
    if errors:
        print(f"FAILED: {len(errors)} issue(s)")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("ALL CHECKS PASSED")
