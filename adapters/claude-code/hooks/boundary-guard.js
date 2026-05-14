// DEEPSHIP Boundary Guard — work unit boundary, Bash classification, anti-bypass.
// Requires policy-gate.js.

var pg = require('./policy-gate.js');

// ── Work unit boundary ───────────────────────────────────

function globToRegExp(glob) {
  var escaped = glob.replace(/\\/g, '/').replace(/[.+^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '.*');
  return new RegExp('^' + escaped + '$');
}

function isTrustedWriteTarget(target) {
  return pg.getTrustedWriteRoots().some(function(trustedRoot) { return pg.isWithin(target, trustedRoot); });
}

function allowedByWorkUnit(target, root, workUnit) {
  var allowed = Array.isArray(workUnit && workUnit.files_allowed) ? workUnit.files_allowed : [];
  var targetNorm = pg.normalize(target);

  return allowed.some(function(entry) {
    if (typeof entry !== 'string' || !entry.trim()) return false;
    var raw = entry.replace(/\\/g, '/');
    var absolute = require('path').isAbsolute(raw) ? raw : require('path').join(root, raw);
    var pattern = pg.normalize(absolute);
    if (pattern.includes('*')) return globToRegExp(pattern).test(targetNorm);
    return targetNorm === pattern || pg.isWithin(targetNorm, pattern);
  });
}

// ── Bash classification ──────────────────────────────────

var READ_ONLY_PATTERNS = [
  /^git\s+status/, /^git\s+log/, /^git\s+diff/, /^git\s+show/,
  /^git\s+branch(?!\s+-[dD])/, /^git\s+rev-parse/, /^git\s+rev-list/,
  /^git\s+ls-/, /^git\s+remote\s+-v/, /^git\s+stash\s+list/,
  /^ls\b/, /^dir\b/, /^cat\b/, /^type\b/, /^head\b/, /^tail\b/,
  /^echo\b/, /^printf\b/, /^cd\b/,
  /^npm\s+list/, /^npm\s+view/, /^npm\s+info/,
  /^pip\s+list/, /^pip\s+show/, /^pip\s+freeze/,
  /^python\s+-c\b/, /^python\s+-m\s+unittest\b/,
  /^node\s+-[ev]/, /^node\s+--version/, /^node\s+--eval/,
  /^which\b/, /^where\b/, /^wc\b/, /^find\b/, /^grep\b/, /^rg\b/,
  /^du\b/, /^df\b/, /^env\b/, /^printenv\b/,
  /^curl\s+.*\bhead\b/i,
];

var DESTRUCTIVE_PATTERNS = [
  /[|&;]\s*(?:>{1,2})/,
  /(?:^|\s)rm\b/, /(?:^|\s)mv\b/, /(?:^|\s)cp\b/,
  /(?:^|\s)mkdir\b/, /(?:^|\s)rmdir\b/,
  /(?:^|\s)npm\s+install/, /(?:^|\s)npm\s+uninstall/, /(?:^|\s)npm\s+run\b/,
  /(?:^|\s)pip\s+install/, /(?:^|\s)pip\s+uninstall/,
  /(?:^|\s)pytest/, /(?:^|\s)python\s+-m\s+pytest/,
  /(?:^|\s)npx\b/, /(?:^|\s)yarn\b/, /(?:^|\s)pnpm\b/,
  /(?:^|\s)cargo\s+(?:build|test|run|install)/,
  /(?:^|\s)make\b/, /(?:^|\s)cmake\b/,
  /(?:^|\s)go\s+(?:build|test|run|install|mod)/,
  /(?:^|\s)rustc\b/, /(?:^|\s)gcc\b/, /(?:^|\s)g\+\+\b/,
  /(?:^|\s)docker\b/, /(?:^|\s)kubectl\b/,
  /(?:^|\s)chmod\b/, /(?:^|\s)chown\b/,
  /(?:^|\s)shutdown\b/, /(?:^|\s)reboot\b/,
  /(?:^|\s)taskkill\b/, /(?:^|\s)tskill\b/,
  /(?:^|\s)wget\b/, /(?:^|\s)curl\b/,
];

var DEEPSHIP_FRAMEWORK_PATTERNS = [
  /python\s+adapters\/cc\/transition_state\.py/,
  /python\s+adapters\/parallel\/rotate\.py/,
  /python\s+adapters\/parallel\/dispatcher\.py/,
  /python\s+adapters\/parallel\/collector\.py/,
  /python\s+checks\/verify\.py/,
  /python\s+adapters\/lane\/lane\.py/,
  /python\s+adapters\/session\/session\.py/,
];

function isReadOnlyBash(command) {
  var cmd = (command || '').trim();
  if (!cmd) return true;

  if (/[^=]>>/.test(cmd) || /[^=]>[^>=]/.test(cmd)) return false;
  if (/\bSet-Content\b/i.test(cmd)) return false;
  if (/\bOut-File\b/i.test(cmd)) return false;

  for (var i = 0; i < DESTRUCTIVE_PATTERNS.length; i++) {
    if (DESTRUCTIVE_PATTERNS[i].test(cmd)) return false;
  }
  for (var j = 0; j < READ_ONLY_PATTERNS.length; j++) {
    if (READ_ONLY_PATTERNS[j].test(cmd)) return true;
  }
  for (var k = 0; k < DEEPSHIP_FRAMEWORK_PATTERNS.length; k++) {
    if (DEEPSHIP_FRAMEWORK_PATTERNS[k].test(cmd)) return true;
  }
  return false;
}

function commandChainHasExec(command) {
  var parts = (command || '').split(/[;&]|\|{1,2}|&&|\|\|/);
  return parts.some(function(part) { return !isReadOnlyBash(part.trim()); });
}

// ── Anti-bypass: Bash file writes ─────────────────────────

function shellTokenPattern(target) {
  var escaped = target.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/\//g, '[\\\\/]');
  return new RegExp('(^|[^\\w.\\\\/-])(?:\\.?[\\\\/])?' + escaped + '(?=$|[\\s\'"])', 'i');
}

function bashWritesMetadata(command) {
  var metadataTargets = [
    '.deepship/state.json', '.deepship/work_units.json', '.deepship/log.jsonl',
    '.deepship/continuation.md',
    'Documentation.md', 'Plan.md', 'Prompt.md',
    '.claude/DEEPSHIP/Documentation.md', '.claude/DEEPSHIP/Plan.md', '.claude/DEEPSHIP/Prompt.md',
  ];
  var writeOperators = /(^|[\s|;&])(?:>{1,2}|Set-Content|Out-File|Add-Content|tee)(?:\s+-(?:LiteralPath|FilePath|Path|Append|Encoding|NoNewline|Force|InputObject)(?:\s+("[^"]*"|'[^']*'|[^\s|;&]+))?)*\s+/i;
  if (!writeOperators.test(command)) return null;
  for (var i = 0; i < metadataTargets.length; i++) {
    if (shellTokenPattern(metadataTargets[i]).test(command)) return metadataTargets[i];
  }
  return null;
}

function looksLikeFileWrite(command) {
  var cmd = (command || '').trim();
  if (!cmd) return false;
  if (/[^=]>>?\s*\S/.test(cmd)) return true;
  if (/\bcp\b/.test(cmd)) return true;
  if (/\bmv\b/.test(cmd)) return true;
  if (/\brm\b/.test(cmd)) return true;
  if (/\btouch\b/.test(cmd)) return true;
  if (/\bsed\b.*-i/.test(cmd)) return true;
  if (/\bSet-Content\b/i.test(cmd)) return true;
  if (/\bAdd-Content\b/i.test(cmd)) return true;
  if (/\bOut-File\b/i.test(cmd)) return true;
  if (/\bpython\b/.test(cmd) && (/-c\b/.test(cmd) || /\S+\.py\b/.test(cmd))) return true;
  if (/\bnode\b/.test(cmd) && (/-e\b/.test(cmd) || /\S+\.js\b/.test(cmd))) return true;
  if (/\bperl\b/.test(cmd) && (/-e\b/.test(cmd) || /\S+\.pl\b/.test(cmd))) return true;
  if (/\bruby\b/.test(cmd) && (/-e\b/.test(cmd) || /\S+\.rb\b/.test(cmd))) return true;
  return false;
}

module.exports = {
  globToRegExp: globToRegExp,
  isTrustedWriteTarget: isTrustedWriteTarget,
  allowedByWorkUnit: allowedByWorkUnit,
  isReadOnlyBash: isReadOnlyBash,
  commandChainHasExec: commandChainHasExec,
  bashWritesMetadata: bashWritesMetadata,
  looksLikeFileWrite: looksLikeFileWrite,
};
