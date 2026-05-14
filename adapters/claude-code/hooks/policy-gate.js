// DEEPSHIP Policy Gate — base layer: permissions matrix, path classification, deny.
// Required by boundary-guard.js and coordination-guard.js.

const fs = require('fs');
const path = require('path');

const WRITE_TOOLS = new Set(['Write', 'Edit', 'MultiEdit']);
const SKILL_TOOL = 'Skill';

const POLICY = {
  'READ_CONTEXT':     { state_write: true,  doc_write: false, code_write: false, exec: false, skill_auto: false },
  'CLARIFY_INTENT':   { state_write: true,  doc_write: true,  code_write: false, exec: false, skill_auto: true  },
  'MAP_REALITY':      { state_write: false, doc_write: false, code_write: false, exec: false, skill_auto: false },
  'SELECT_MILESTONE': { state_write: true,  doc_write: false, code_write: false, exec: false, skill_auto: false },
  'PLAN_STEP':        { state_write: true,  doc_write: true,  code_write: false, exec: false, skill_auto: true  },
  'EXECUTE':          { state_write: true,  doc_write: true,  code_write: true,  exec: true,  skill_auto: true  },
  'VALIDATE':         { state_write: false, doc_write: false, code_write: false, exec: true,  skill_auto: false },
  'REPAIR':           { state_write: false, doc_write: false, code_write: true,  exec: true,  skill_auto: false },
  'RECORD':           { state_write: true,  doc_write: true,  code_write: false, exec: false, skill_auto: false },
  'ADVANCE':          { state_write: true,  doc_write: true,  code_write: false, exec: false, skill_auto: false },
  'BLOCK':            { state_write: true,  doc_write: true,  code_write: false, exec: false, skill_auto: false },
  'COMPLETE':         { state_write: true,  doc_write: true,  code_write: false, exec: false, skill_auto: false },
};

const TRUSTED_CONFIG = path.join(process.env.USERPROFILE || process.env.HOME || '', '.claude', 'deepship-policy.json');
const DEEPSHIP_STATE_FILES = ['state.json', 'work_units.json', 'log.jsonl'];
const PROJECT_DOC_FILES = ['Documentation.md', 'CHANGELOG.md', 'README.md', 'Prompt.md', 'Plan.md'];

function deny(reason, ruleId) {
  process.stdout.write(JSON.stringify({
    hookSpecificOutput: {
      hookEventName: 'PreToolUse',
      permissionDecision: 'deny',
      permissionDecisionReason: reason,
      ruleId: ruleId || '',
    },
  }));
}

function normalize(p) {
  return path.resolve(p).replace(/\\/g, '/').toLowerCase();
}

function isWithin(child, parent) {
  var c = normalize(child);
  var p = normalize(parent);
  return c === p || c.startsWith(p.endsWith('/') ? p : p + '/');
}

function findProjectRoot(start) {
  var current = path.resolve(start || process.cwd());
  for (;;) {
    if (fs.existsSync(path.join(current, '.deepship', 'state.json')) ||
        fs.existsSync(path.join(current, '.deepship', 'work_units.json'))) {
      return current;
    }
    var parentDir = path.dirname(current);
    if (parentDir === current) return null;
    current = parentDir;
  }
}

function readJson(file) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8').replace(/^﻿/, ''));
  } catch (_) {
    return null;
  }
}

function splitPathList(value) {
  if (!value) return [];
  return value.split(path.delimiter).map(function(e) { return e.trim(); }).filter(Boolean);
}

function getTrustedWriteRoots() {
  var roots = splitPathList(process.env.DEEPSHIP_TRUSTED_WRITE_ROOTS);
  var config = readJson(TRUSTED_CONFIG);
  if (Array.isArray(config && config.trusted_write_roots)) {
    roots.push.apply(roots, config.trusted_write_roots);
  }
  return roots.filter(function(e) { return typeof e === 'string' && e.trim(); });
}

function looksLikeDeepShipFramework(cwd) {
  var markers = ['core/manifest.md', 'protocol/state-machine.md', 'checks/verify.py'];
  return markers.every(function(m) { return fs.existsSync(path.join(cwd, m)); });
}

function getTargetPath(toolName, toolInput) {
  if (!WRITE_TOOLS.has(toolName)) return null;
  return (toolInput && toolInput.file_path) || (toolInput && toolInput.path) || null;
}

function isMetadataWrite(target, root) {
  var rel = path.relative(root, target).replace(/\\/g, '/');
  return rel === '.deepship/state.json' || rel === '.deepship/work_units.json' ||
    rel === '.deepship/log.jsonl' || rel === 'Documentation.md' || rel === 'Plan.md' ||
    rel === '.claude/DEEPSHIP/Documentation.md' || rel === '.claude/DEEPSHIP/Plan.md' ||
    rel.startsWith('.claude/plans/');
}

function isDynamicPlanningArtifact(target, root) {
  var rel = path.relative(root, target).replace(/\\/g, '/');
  return rel === '.deepship/sessions.json' || rel.startsWith('.deepship/a2a/') ||
    rel.startsWith('.deepship/prompt-supplements/') || rel.startsWith('.deepship/plan-revisions/');
}

function isBootstrapWrite(target, root) {
  var rel = path.relative(root, target).replace(/\\/g, '/');
  return rel === '.deepship/state.json' || rel === '.deepship/work_units.json' ||
    rel === '.deepship/log.jsonl' || rel === 'Prompt.md' || rel === 'Plan.md' ||
    rel === 'Documentation.md' || rel === '.claude/DEEPSHIP/Prompt.md' ||
    rel === '.claude/DEEPSHIP/Plan.md' || rel === '.claude/DEEPSHIP/Documentation.md' ||
    rel.startsWith('.claude/plans/');
}

function writeKind(filePath, root) {
  var fp = (filePath || '').replace(/\\/g, '/');
  if (fp.includes('.deepship/')) {
    for (var i = 0; i < DEEPSHIP_STATE_FILES.length; i++) {
      var sf = DEEPSHIP_STATE_FILES[i];
      if (fp.endsWith('/' + sf) || fp.endsWith(sf)) return 'state_write';
    }
    if (fp.includes('/runs/') && fp.endsWith('.json')) return 'state_write';
    return 'doc_write';
  }
  for (var j = 0; j < PROJECT_DOC_FILES.length; j++) {
    var df = PROJECT_DOC_FILES[j];
    if (fp.endsWith(df) || fp.endsWith('/' + df)) return 'doc_write';
  }
  if (fp.endsWith('.md') && (fp.includes('/docs/') || fp.split('/').length <= 2)) return 'doc_write';
  if (fp.includes('.claude/plans/') && fp.endsWith('.md')) return 'doc_write';
  if ((fp.includes('/.planning/') || fp.includes('/planning/')) && fp.endsWith('.md')) return 'doc_write';
  if ((fp.includes('/plans/') || fp.includes('/.plans/')) && fp.endsWith('.md')) return 'doc_write';
  return 'code_write';
}

function isPlanWrite(target, root) {
  var rel = path.relative(root, target).replace(/\\/g, '/');
  return rel === '.deepship/work_units.json' || rel === '.deepship/sessions.json' ||
    rel.startsWith('.deepship/a2a/') || rel.startsWith('.deepship/prompt-supplements/') ||
    rel.startsWith('.deepship/plan-revisions/') || rel === 'Plan.md' ||
    rel === '.claude/DEEPSHIP/Plan.md' || rel.startsWith('.claude/plans/');
}

function isRootWorkUnitsFile(target, root) {
  return path.relative(root, target).replace(/\\/g, '/') === '.deepship/work_units.json';
}

function isRootMetadataFile(target, root) {
  var rel = path.relative(root, target).replace(/\\/g, '/');
  return rel === '.deepship/state.json' || rel === '.deepship/work_units.json' ||
    rel === '.deepship/log.jsonl';
}

function isInitialProjectTruthWrite(target, root) {
  var rel = path.relative(root, target).replace(/\\/g, '/');
  return (rel === 'Prompt.md' || rel === 'Documentation.md' ||
    rel === '.claude/DEEPSHIP/Prompt.md' || rel === '.claude/DEEPSHIP/Documentation.md') &&
    !fs.existsSync(target);
}

module.exports = {
  WRITE_TOOLS: WRITE_TOOLS,
  SKILL_TOOL: SKILL_TOOL,
  POLICY: POLICY,
  deny: deny,
  normalize: normalize,
  isWithin: isWithin,
  findProjectRoot: findProjectRoot,
  readJson: readJson,
  getTrustedWriteRoots: getTrustedWriteRoots,
  looksLikeDeepShipFramework: looksLikeDeepShipFramework,
  getTargetPath: getTargetPath,
  writeKind: writeKind,
  isMetadataWrite: isMetadataWrite,
  isDynamicPlanningArtifact: isDynamicPlanningArtifact,
  isBootstrapWrite: isBootstrapWrite,
  isPlanWrite: isPlanWrite,
  isRootWorkUnitsFile: isRootWorkUnitsFile,
  isRootMetadataFile: isRootMetadataFile,
  isInitialProjectTruthWrite: isInitialProjectTruthWrite,
};
