// DEEPSHIP Coordination Guard — lane contracts, session ownership, WU integrity, transition validation.
// Requires policy-gate.js.

var pg = require('./policy-gate.js');
var path = require('path');

// ── Transition validation ─────────────────────────────────

var TRANSITION_TOOLS = new Set(['transition_state', 'transitionstate', 'TransitionState']);
var LEGAL_TRANSITIONS = {
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

function validateTransition(root, toolInput) {
  var target = ((toolInput && toolInput.target) || (toolInput && toolInput.to) || '').toUpperCase();
  if (!target) return 'DEEPSHIP BLOCK: transition_state requires target/to parameter';
  var state = pg.readJson(path.join(root, '.deepship', 'state.json'));
  var currentState = ((state && state.current_state) || 'READ_CONTEXT').toUpperCase();
  var allowed = LEGAL_TRANSITIONS[currentState];
  if (!allowed || !allowed.has(target)) {
    var legal = allowed ? Array.from(allowed).join(', ') : '(terminal)';
    return 'DEEPSHIP BLOCK: illegal transition ' + currentState + ' -> ' + target + '. Legal: ' + legal;
  }
  return null;
}

// ── Work unit helpers ─────────────────────────────────────

function parseJsonText(value) {
  if (typeof value !== 'string' || !value.trim()) return null;
  try { return JSON.parse(value.replace(/^﻿/, '')); } catch (_) { return null; }
}

function workUnitIds(data) {
  var units = Array.isArray(data && data.work_units) ? data.work_units : [];
  var ids = [];
  for (var i = 0; i < units.length; i++) {
    if (units[i] && typeof units[i].id === 'string') ids.push(units[i].id);
  }
  return new Set(ids);
}

// ── Lane helpers ──────────────────────────────────────────

function activeLanes(root) {
  var registry = pg.readJson(path.join(root, '.deepship', 'lanes.json'));
  var lanes = Array.isArray(registry && registry.lanes) ? registry.lanes : [];
  return lanes.filter(function(lane) { return lane && lane.status === 'active'; });
}

function activeLaneForTarget(target, root) {
  var lanes = activeLanes(root);
  for (var i = 0; i < lanes.length; i++) {
    var lane = lanes[i];
    var laneRoot = lane.worktree_path || null;
    if (laneRoot && pg.isWithin(target, laneRoot)) return lane;
    var laneHome = lane.lane_home || (laneRoot ? path.join(laneRoot, '.deepship') : null);
    if (laneHome && pg.isWithin(target, laneHome)) return lane;
  }
  return null;
}

function laneNameFromPath(target, root) {
  var rel = path.relative(root, target).replace(/\\/g, '/');
  var parts = rel.split('/');
  if (parts[0] === '.deepship' && parts[1] === 'lanes' && parts[2]) return parts[2];
  return null;
}

function laneHasA2AContract(root, laneName) {
  var direct = path.join(root, '.deepship', 'a2a', laneName + '.json');
  if (require('fs').existsSync(direct)) return true;
  var dir = path.join(root, '.deepship', 'a2a');
  try {
    return require('fs').readdirSync(dir).some(function(entry) {
      return entry.endsWith('.json') && entry.includes(laneName);
    });
  } catch (_) { return false; }
}

// ── Lane guards ───────────────────────────────────────────

function laneCreationContractViolation(target, root) {
  var laneName = laneNameFromPath(target, root);
  if (!laneName) return null;
  if (activeLaneForTarget(target, root)) return null;
  if (laneHasA2AContract(root, laneName)) return null;
  return laneName;
}

function laneMetadataDirectWriteViolation(target, root, cwd) {
  var lane = activeLaneForTarget(target, root);
  if (!lane) return null;
  var laneRoot = lane.worktree_path || null;
  if (laneRoot && pg.isWithin(cwd, laneRoot)) return null;
  return lane.name || lane.worktree_path || 'unknown';
}

// ── Session ownership ────────────────────────────────────

function requiresRootSessionOwner(target, root, cwd) {
  if (!pg.isRootMetadataFile(target, root)) return null;
  if (activeLanes(root).length === 0) return null;
  var session = pg.readJson(path.join(root, '.deepship', 'session.json'));
  if (!(session && session.owner_worktree)) {
    return 'active lanes exist; claim session ownership before writing root metadata';
  }
  if (pg.normalize(session.owner_worktree) !== pg.normalize(cwd)) {
    return 'not session owner. Owner worktree: ' + session.owner_worktree + ', current: ' + cwd;
  }
  return null;
}

// ── WU integrity ──────────────────────────────────────────

var LEGAL_WU_STATUS_TRANSITIONS = {
  pending: new Set(['pending', 'in_progress', 'blocked', 'failed']),
  in_progress: new Set(['in_progress', 'done', 'blocked', 'failed']),
  done: new Set(['done', 'integrated', 'failed']),
  integrated: new Set(['integrated']),
  blocked: new Set(['blocked', 'in_progress', 'failed']),
  failed: new Set(['failed', 'pending']),
};

function workUnitsIntegrityViolation(target, root, toolInput) {
  if (!pg.isRootWorkUnitsFile(target, root)) return null;

  var proposed = parseJsonText(toolInput && toolInput.content);
  if (!proposed) return null;

  var current = pg.readJson(path.join(root, '.deepship', 'work_units.json'));
  if (!current) return null;

  var st = pg.readJson(path.join(root, '.deepship', 'state.json'));
  var cs = ((st && st.current_state) || '').toUpperCase();
  var stateAllowsArchive = pg.POLICY[cs] && pg.POLICY[cs].state_write;
  var milestoneChanged = proposed.milestone && current.milestone &&
    proposed.milestone !== current.milestone;
  var canArchiveIntegrated = stateAllowsArchive || milestoneChanged;

  var oldUnits = Array.isArray(current.work_units) ? current.work_units : [];
  var newUnits = Array.isArray(proposed.work_units) ? proposed.work_units : [];
  var newById = new Map();
  for (var i = 0; i < newUnits.length; i++) {
    if (newUnits[i] && newUnits[i].id) newById.set(newUnits[i].id, newUnits[i]);
  }

  for (var j = 0; j < oldUnits.length; j++) {
    var oldUnit = oldUnits[j];
    if (!oldUnit || !oldUnit.id) continue;
    var oldStatus = oldUnit.status || 'pending';
    var newUnit = newById.get(oldUnit.id);
    if (!newUnit) {
      if (oldStatus === 'integrated' && canArchiveIntegrated) continue;
      if (oldStatus !== 'pending') {
        return 'cannot remove active WU ' + oldUnit.id + ' with status ' + oldStatus;
      }
      continue;
    }
    var newStatus = newUnit.status || 'pending';
    var legalTargets = LEGAL_WU_STATUS_TRANSITIONS[oldStatus];
    if (legalTargets && !legalTargets.has(newStatus)) {
      return 'illegal WU status transition ' + oldUnit.id + ': ' + oldStatus + ' -> ' + newStatus;
    }
  }
  return null;
}

// ── Lane collision guards ─────────────────────────────────

function activeLaneMetadataCollision(target, root, toolInput) {
  if (!pg.isRootMetadataFile(target, root)) return null;
  var proposed = parseJsonText(toolInput && toolInput.content);
  if (!proposed) return null;

  var lanes = activeLanes(root);
  for (var i = 0; i < lanes.length; i++) {
    var lane = lanes[i];
    var laneHome = lane.lane_home || (lane.worktree_path ? path.join(lane.worktree_path, '.deepship') : null);
    if (!laneHome) continue;

    var laneState = pg.readJson(path.join(laneHome, 'state.json'));
    if (laneState) {
      var sameMilestone = proposed.current_milestone && laneState.current_milestone &&
        proposed.current_milestone === laneState.current_milestone;
      var sameWu = proposed.current_work_unit && laneState.current_work_unit &&
        proposed.current_work_unit === laneState.current_work_unit;
      if (sameMilestone || sameWu) return lane.name || lane.worktree_path || 'unknown';
    }
    var laneWorkUnits = pg.readJson(path.join(laneHome, 'work_units.json'));
    if (laneWorkUnits && proposed.milestone && proposed.milestone === laneWorkUnits.milestone) {
      return lane.name || lane.worktree_path || 'unknown';
    }
  }
  return null;
}

function activeLaneCollision(target, root, toolInput) {
  if (!pg.isRootWorkUnitsFile(target, root)) return null;
  var proposed = parseJsonText(toolInput && toolInput.content);
  if (!proposed) return null;

  var lanes = activeLanes(root);
  var proposedIds = workUnitIds(proposed);
  for (var i = 0; i < lanes.length; i++) {
    var lane = lanes[i];
    var laneHome = lane.lane_home || (lane.worktree_path ? path.join(lane.worktree_path, '.deepship') : null);
    if (!laneHome) continue;
    var laneWorkUnits = pg.readJson(path.join(laneHome, 'work_units.json'));
    if (!laneWorkUnits) continue;
    if (proposed.milestone && laneWorkUnits.milestone && proposed.milestone === laneWorkUnits.milestone) {
      return lane.name || lane.worktree_path || 'unknown';
    }
    var laneIds = workUnitIds(laneWorkUnits);
    laneIds.forEach(function(id) { if (proposedIds.has(id)) return lane.name || lane.worktree_path || 'unknown'; });
  }
  // Re-check manually due to forEach limitation
  for (var j = 0; j < lanes.length; j++) {
    var ln = lanes[j];
    var lh = ln.lane_home || (ln.worktree_path ? path.join(ln.worktree_path, '.deepship') : null);
    if (!lh) continue;
    var lwu = pg.readJson(path.join(lh, 'work_units.json'));
    if (!lwu) continue;
    var lids = workUnitIds(lwu);
    var collision = false;
    lids.forEach(function(id) { if (proposedIds.has(id)) collision = true; });
    if (collision) return ln.name || ln.worktree_path || 'unknown';
  }
  return null;
}

module.exports = {
  TRANSITION_TOOLS: TRANSITION_TOOLS,
  LEGAL_TRANSITIONS: LEGAL_TRANSITIONS,
  validateTransition: validateTransition,
  laneCreationContractViolation: laneCreationContractViolation,
  laneMetadataDirectWriteViolation: laneMetadataDirectWriteViolation,
  requiresRootSessionOwner: requiresRootSessionOwner,
  workUnitsIntegrityViolation: workUnitsIntegrityViolation,
  activeLaneMetadataCollision: activeLaneMetadataCollision,
  activeLaneCollision: activeLaneCollision,
};
