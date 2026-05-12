#!/usr/bin/env node
// DEEPSHIP Policy Guard - PreToolUse hook for Write/Edit/MultiEdit.
//
// This is a Claude Code adapter guard, not the full DEEPSHIP runtime.
// It only enforces projects that have a .deepship/ state directory.

const fs = require('fs');
const path = require('path');

const WRITE_TOOLS = new Set(['Write', 'Edit', 'MultiEdit']);
const CODE_WRITE_STATES = new Set(['EXECUTE', 'REPAIR']);
const TRUSTED_CONFIG = path.join(process.env.USERPROFILE || process.env.HOME || '', '.claude', 'deepship-policy.json');

function deny(reason) {
  process.stdout.write(JSON.stringify({
    hookSpecificOutput: {
      hookEventName: 'PreToolUse',
      permissionDecision: 'deny',
      permissionDecisionReason: reason,
    },
  }));
}

function normalize(p) {
  return path.resolve(p).replace(/\\/g, '/').toLowerCase();
}

function isWithin(child, parent) {
  const c = normalize(child);
  const p = normalize(parent);
  return c === p || c.startsWith(p.endsWith('/') ? p : `${p}/`);
}

function findProjectRoot(start) {
  let current = path.resolve(start || process.cwd());
  for (;;) {
    const statePath = path.join(current, '.deepship', 'state.json');
    const wusPath = path.join(current, '.deepship', 'work_units.json');
    if (fs.existsSync(statePath) || fs.existsSync(wusPath)) {
      return current;
    }
    const parent = path.dirname(current);
    if (parent === current) return null;
    current = parent;
  }
}

function readJson(file) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8').replace(/^\uFEFF/, ''));
  } catch {
    return null;
  }
}

function splitPathList(value) {
  if (!value) return [];
  return value
    .split(path.delimiter)
    .map((entry) => entry.trim())
    .filter(Boolean);
}

function getTrustedWriteRoots() {
  const roots = splitPathList(process.env.DEEPSHIP_TRUSTED_WRITE_ROOTS);
  const config = readJson(TRUSTED_CONFIG);
  if (Array.isArray(config?.trusted_write_roots)) {
    roots.push(...config.trusted_write_roots);
  }
  return roots.filter((entry) => typeof entry === 'string' && entry.trim());
}


function looksLikeDeepShipFramework(cwd) {
  const markers = ['core/manifest.md', 'protocol/state-machine.md', 'checks/verify.py'];
  return markers.every(function(m) { return fs.existsSync(path.join(cwd, m)); });
}

function getTargetPath(toolName, toolInput) {
  if (!WRITE_TOOLS.has(toolName)) return null;
  return toolInput?.file_path || toolInput?.path || null;
}

function isMetadataWrite(target, root) {
  const rel = path.relative(root, target).replace(/\\/g, '/');
  return (
    rel === '.deepship/state.json' ||
    rel === '.deepship/work_units.json' ||
    rel === '.deepship/log.jsonl' ||
    rel === 'Documentation.md' ||
    rel === 'Plan.md' ||
    rel === '.claude/DEEPSHIP/Documentation.md' ||
    rel === '.claude/DEEPSHIP/Plan.md'
  );
}

function isBootstrapWrite(target, root) {
  const rel = path.relative(root, target).replace(/\\/g, '/');
  return (
    rel === '.deepship/state.json' ||
    rel === '.deepship/work_units.json' ||
    rel === '.deepship/log.jsonl' ||
    rel === 'Prompt.md' ||
    rel === 'Plan.md' ||
    rel === 'Documentation.md' ||
    rel === '.claude/DEEPSHIP/Prompt.md' ||
    rel === '.claude/DEEPSHIP/Plan.md' ||
    rel === '.claude/DEEPSHIP/Documentation.md'
  );
}


const DEEPSHIP_STATE_FILES = ['state.json', 'work_units.json', 'log.jsonl'];
const PROJECT_DOC_FILES = ['Documentation.md', 'CHANGELOG.md', 'README.md', 'Prompt.md', 'Plan.md'];

function writeKind(filePath, root) {
  const fp = (filePath || '').replace(/\\/g, '/');
  if (fp.includes('.deepship/')) {
    for (const sf of DEEPSHIP_STATE_FILES) {
      if (fp.endsWith('/' + sf) || fp.endsWith(sf)) return 'state_write';
    }
    if (fp.includes('/runs/') && fp.endsWith('.json')) return 'state_write';
    return 'doc_write';
  }
  for (const df of PROJECT_DOC_FILES) {
    if (fp.endsWith(df) || fp.endsWith('/' + df)) return 'doc_write';
  }
  if (fp.endsWith('.md') && (fp.includes('/docs/') || fp.split('/').length <= 2)) return 'doc_write';
  return 'code_write';
}

function isPlanWrite(target, root) {
  const rel = path.relative(root, target).replace(/\\/g, '/');
  return (
    rel === '.deepship/work_units.json' ||
    rel === 'Plan.md' ||
    rel === '.claude/DEEPSHIP/Plan.md'
  );
}

function isInitialProjectTruthWrite(target, root) {
  const rel = path.relative(root, target).replace(/\\/g, '/');
  const isProjectTruthFile = (
    rel === 'Prompt.md' ||
    rel === 'Documentation.md' ||
    rel === '.claude/DEEPSHIP/Prompt.md' ||
    rel === '.claude/DEEPSHIP/Documentation.md'
  );
  return isProjectTruthFile && !fs.existsSync(target);
}

function globToRegExp(glob) {
  const escaped = glob
    .replace(/\\/g, '/')
    .replace(/[.+^${}()|[\]\\]/g, '\\$&')
    .replace(/\*/g, '.*');
}

function allowedByWorkUnit(target, root, workUnit) {
  const allowed = Array.isArray(workUnit?.files_allowed) ? workUnit.files_allowed : [];
  const targetNorm = normalize(target);

  return allowed.some((entry) => {
    if (typeof entry !== 'string' || !entry.trim()) return false;
    const raw = entry.replace(/\\/g, '/');
    const absolute = path.isAbsolute(raw) ? raw : path.join(root, raw);
    const pattern = normalize(absolute);
    if (pattern.includes('*')) {
      return globToRegExp(pattern).test(targetNorm);
    }
    return targetNorm === pattern || isWithin(targetNorm, pattern);
  });
}

function isTrustedWriteTarget(target) {
  return getTrustedWriteRoots().some((trustedRoot) => isWithin(target, trustedRoot));
}

function shellTokenPattern(target) {
  const escaped = target.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/\//g, '[\\\\/]');
  return new RegExp(`(^|[^\\w.\\\\/-])(?:\\.?[\\\\/])?${escaped}(?=$|[\\s'"])`, 'i');
}

function bashWritesMetadata(command) {
  const metadataTargets = [
    '.deepship/state.json', '.deepship/work_units.json', '.deepship/log.jsonl',
    '.deepship/continuation.md',
    'Documentation.md', 'Plan.md', 'Prompt.md',
    '.claude/DEEPSHIP/Documentation.md', '.claude/DEEPSHIP/Plan.md', '.claude/DEEPSHIP/Prompt.md',
  ];
  const writeOperators = /(^|[\s|;&])(?:>{1,2}|Set-Content|Out-File|Add-Content|tee)(?:\s+-(?:LiteralPath|FilePath|Path|Append|Encoding|NoNewline|Force|InputObject)(?:\s+("[^"]*"|'[^']*'|[^\s|;&]+))?)*\s+/i;
  if (!writeOperators.test(command)) return null;
  return metadataTargets.find((target) => shellTokenPattern(target).test(command)) || null;
}

async function main() {

const TRANSITION_TOOLS = new Set(['transition_state', 'transitionstate', 'TransitionState']);
const LEGAL_TRANSITIONS = {
  'READ_CONTEXT':     new Set(['CLARIFY_INTENT', 'MAP_REALITY']),
  'CLARIFY_INTENT':   new Set(['MAP_REALITY', 'BLOCK']),
  'MAP_REALITY':      new Set(['SELECT_MILESTONE', 'BLOCK']),
  'SELECT_MILESTONE': new Set(['PLAN_STEP', 'BLOCK']),
  'PLAN_STEP':        new Set(['EXECUTE']),
  'EXECUTE':          new Set(['VALIDATE']),
  'VALIDATE':         new Set(['RECORD', 'REPAIR']),
  'REPAIR':           new Set(['VALIDATE', 'BLOCK']),
  'RECORD':           new Set(['ADVANCE']),
  'ADVANCE':          new Set(['READ_CONTEXT', 'COMPLETE']),
  'BLOCK':            new Set(['READ_CONTEXT']),
  'COMPLETE':         new Set(['READ_CONTEXT']),
};
  let input = '';
  for await (const chunk of process.stdin) input += chunk;

  let data;
  try {
    data = JSON.parse(input.replace(/^\uFEFF/, ''));
  } catch {
    return;
  }

  const toolName = data.tool_name;
  const cwd = data.cwd || process.cwd();
  const root = findProjectRoot(cwd);

  // Transition validation
  if (TRANSITION_TOOLS.has(toolName)) {
    const target = (data.tool_input?.target || data.tool_input?.to || '').toUpperCase();
    if (!target) {
      deny('DEEPSHIP BLOCK: transition_state requires target/to parameter');
      return;
    }
    const state = readJson(path.join(root, '.deepship', 'state.json'));
    const currentState = (state?.current_state || 'READ_CONTEXT').toUpperCase();
    const allowed = LEGAL_TRANSITIONS[currentState];
    if (!allowed || !allowed.has(target)) {
      const legal = allowed ? Array.from(allowed).join(', ') : '(terminal)';
      deny('DEEPSHIP BLOCK: illegal transition ' + currentState + ' -> ' + target + '. Legal: ' + legal);
      return;
    }
    return; // transition valid
  }

  
  // Bash metadata write interception
  if (toolName === 'Bash' || toolName === 'bash') {
    var cmd = (data.tool_input && data.tool_input.command || '').toString();
    var metadataTarget = cmd ? bashWritesMetadata(cmd) : null;
    if (metadataTarget) {
      deny('DEEPSHIP BLOCK: Bash command redirects to metadata file ' + metadataTarget +
           '. Use transition_state.py for state changes, RECORD state for documentation.');
      return;
    }
  }

  if (!WRITE_TOOLS.has(toolName)) return;

  const target = getTargetPath(toolName, data.tool_input || {});
  if (!target) return;

  // Non-DEEPSHIP projects are not blocked by this adapter hook.
  if (!root) {
    if (looksLikeDeepShipFramework(cwd)) {
      deny('DEEPSHIP BLOCK: DEEPSHIP framework repo has no .deepship/ state. Initialize dogfood state first: mkdir -p .deepship && copy templates from ~/.claude/DEEPSHIP/templates/');
      return;
    }
    return;
  }

  const targetAbs = path.resolve(cwd, target);
  if (!isWithin(targetAbs, root)) {
    if (isTrustedWriteTarget(targetAbs)) return;
    deny(`DEEPSHIP BLOCK: write target is outside project root: ${targetAbs}`);
    return;
  }

  const statePath = path.join(root, '.deepship', 'state.json');
  const workUnitsPath = path.join(root, '.deepship', 'work_units.json');
  const state = readJson(statePath);
  if (!state?.current_state) {
    if (isBootstrapWrite(targetAbs, root)) return;
    deny('DEEPSHIP BLOCK: .deepship/state.json is missing or invalid; enter READ_CONTEXT/init first.');
    return;
  }

  const currentState = state.current_state;

  if (currentState === 'COMPLETE' || currentState === 'VALIDATE' || currentState === 'ADVANCE') {
    deny(`DEEPSHIP BLOCK: ${currentState} does not allow file writes.`);
    return;
  }

  if (currentState === 'PLAN_STEP') {
    if (isInitialProjectTruthWrite(targetAbs, root)) return;
    if (isPlanWrite(targetAbs, root)) return;
    deny('DEEPSHIP BLOCK: PLAN_STEP may only update planning/work unit files.');
    return;
  }

  if (currentState === 'RECORD') {
    if (isMetadataWrite(targetAbs, root)) return;
    deny('DEEPSHIP BLOCK: RECORD may only update .deepship state/log and project documentation.');
    return;
  }

  if (!CODE_WRITE_STATES.has(currentState)) {
    deny(`DEEPSHIP BLOCK: ${currentState} is not an execution state; read/map/plan before editing.`);
    return;
  }

  if (isMetadataWrite(targetAbs, root)) {
    deny('DEEPSHIP BLOCK: EXECUTE/REPAIR cannot directly edit DEEPSHIP metadata; use RECORD.');
    return;
  }

  const workUnits = readJson(workUnitsPath);
  const currentWuId = state.current_work_unit;
  const units = Array.isArray(workUnits?.work_units) ? workUnits.work_units : [];
  const currentWu = units.find((wu) => wu.id === currentWuId);

  if (!currentWu) {
    deny('DEEPSHIP BLOCK: no current_work_unit found; PLAN_STEP must create/select a work unit before code edits.');
    return;
  }

  if (!allowedByWorkUnit(targetAbs, root, currentWu)) {
    deny(`DEEPSHIP BLOCK: target is outside current work unit files_allowed: ${targetAbs}`);
  }
}

main();
