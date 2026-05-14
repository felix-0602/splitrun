#!/usr/bin/env node
// DEEPSHIP Policy Guard — PreToolUse hook for Write/Edit/MultiEdit.
// Layered architecture: policy-gate → boundary-guard → coordination-guard.
//
// This is a Claude Code adapter guard, not the full DEEPSHIP runtime.
// It only enforces projects that have a .deepship/ state directory.

var pg = require('./policy-gate.js');
var bg = require('./boundary-guard.js');
var cg = require('./coordination-guard.js');
var path = require('path');

async function main() {
  var input = '';
  for await (var chunk of process.stdin) input += chunk;

  var data;
  try { data = JSON.parse(input.replace(/^﻿/, '')); } catch (_) { return; }

  var toolName = data.tool_name;
  var cwd = data.cwd || process.cwd();
  var root = pg.findProjectRoot(cwd);

  // ── Transition validation ─────────────────────────────
  if (cg.TRANSITION_TOOLS.has(toolName)) {
    var transErr = cg.validateTransition(root, data.tool_input);
    if (transErr) { pg.deny(transErr); return; }
    return;
  }

  // ── Skill auto 拦截 ───────────────────────────────────
  if (toolName === pg.SKILL_TOOL && root) {
    var st = pg.readJson(path.join(root, '.deepship', 'state.json'));
    var cs = ((st && st.current_state) || 'READ_CONTEXT').toUpperCase();
    // CC PreToolUse hook 无法区分 skill_user vs skill_auto；仅记录警告不阻断
    // 完整 skill_auto 阻断需等 CC 提供 invocation source 字段
  }

  // ── Bash exec 分类拦截 ────────────────────────────────
  if ((toolName === 'Bash' || toolName === 'bash') && root) {
    var cmd = (data.tool_input && data.tool_input.command || '').toString();

    var metadataTarget = cmd ? bg.bashWritesMetadata(cmd) : null;
    if (metadataTarget) {
      pg.deny('DEEPSHIP BLOCK: Bash command redirects to metadata file ' + metadataTarget +
              '. Use transition_state.py for state changes, RECORD state for documentation.');
      return;
    }

    if (bg.commandChainHasExec(cmd)) {
      var bst = pg.readJson(path.join(root, '.deepship', 'state.json'));
      var bcs = ((bst && bst.current_state) || 'READ_CONTEXT').toUpperCase();
      var bp = pg.POLICY[bcs];
      if (bp && !bp.exec) {
        pg.deny('DEEPSHIP BLOCK: ' + bcs + ' does not allow exec (destructive Bash). Command: ' + cmd.substring(0, 80));
        return;
      }
    }

    if (bg.looksLikeFileWrite(cmd)) {
      var abst = pg.readJson(path.join(root, '.deepship', 'state.json'));
      var abcs = ((abst && abst.current_state) || 'READ_CONTEXT').toUpperCase();
      var abp = pg.POLICY[abcs];
      if (abp && !abp.code_write) {
        pg.deny('DEEPSHIP BLOCK: ' + abcs + ' does not allow code_write — Bash file-write attempt blocked by anti-bypass guard. Use a state that allows code_write, or trigger revolution approval. Command: ' + cmd.substring(0, 100));
        return;
      }
    }
  }

  // ── Write/Edit gate ────────────────────────────────────
  if (!pg.WRITE_TOOLS.has(toolName)) return;

  var target = pg.getTargetPath(toolName, data.tool_input || {});
  if (!target) return;

  if (!root) {
    if (pg.looksLikeDeepShipFramework(cwd)) {
      pg.deny('DEEPSHIP BLOCK: DEEPSHIP framework repo has no .deepship/ state. Initialize dogfood state first: mkdir -p .deepship && copy templates from ~/.claude/DEEPSHIP/templates/');
    }
    return;
  }

  var targetAbs = path.resolve(cwd, target);
  if (!pg.isWithin(targetAbs, root)) {
    if (bg.isTrustedWriteTarget(targetAbs)) return;
    pg.deny('DEEPSHIP BLOCK: write target is outside project root: ' + targetAbs);
    return;
  }

  // ── Coordination guards ────────────────────────────────
  var err;
  err = cg.laneCreationContractViolation(targetAbs, root);
  if (err) { pg.deny("DEEPSHIP BLOCK: lane '" + err + "' cannot be created or written before an A2A contract exists in .deepship/a2a/."); return; }

  err = cg.laneMetadataDirectWriteViolation(targetAbs, root, cwd);
  if (err) { pg.deny('DEEPSHIP BLOCK: main session cannot write active lane metadata directly. Lane: ' + err + '. Open the lane worktree and write there.'); return; }

  err = cg.activeLaneCollision(targetAbs, root, data.tool_input || {});
  if (err) { pg.deny('DEEPSHIP BLOCK: attempted to write active lane work units into main workspace metadata. Lane: ' + err + '. Open the lane worktree and write its .deepship/work_units.json there.'); return; }

  err = cg.activeLaneMetadataCollision(targetAbs, root, data.tool_input || {});
  if (err) { pg.deny('DEEPSHIP BLOCK: attempted to write active lane metadata into main workspace metadata. Lane: ' + err + '.'); return; }

  err = cg.requiresRootSessionOwner(targetAbs, root, cwd);
  if (err) { pg.deny('DEEPSHIP BLOCK: ' + err + '.'); return; }

  err = cg.workUnitsIntegrityViolation(targetAbs, root, data.tool_input || {});
  if (err) { pg.deny('DEEPSHIP BLOCK: ' + err + '.'); return; }

  // ── State-gated permission check ───────────────────────
  var statePath = path.join(root, '.deepship', 'state.json');
  var workUnitsPath = path.join(root, '.deepship', 'work_units.json');
  var state = pg.readJson(statePath);
  if (!(state && state.current_state)) {
    if (pg.isBootstrapWrite(targetAbs, root)) return;
    pg.deny('DEEPSHIP BLOCK: .deepship/state.json is missing or invalid; enter READ_CONTEXT/init first.');
    return;
  }

  var currentState = state.current_state;
  var policy = pg.POLICY[currentState];
  if (!policy) {
    pg.deny("DEEPSHIP BLOCK: unknown state '" + currentState + "' — no policy entry.");
    return;
  }

  var kind = pg.writeKind(targetAbs, root);
  if (pg.isDynamicPlanningArtifact(targetAbs, root) && currentState !== 'PLAN_STEP') {
    pg.deny('DEEPSHIP BLOCK: ' + currentState + ' cannot write dynamic planning artifact (' + targetAbs + '); use PLAN_STEP.');
    return;
  }

  var kindToPolicy = { state_write: 'state_write', doc_write: 'doc_write', code_write: 'code_write' };
  var policyKey = kindToPolicy[kind];
  if (!policyKey) return;

  if (!policy[policyKey]) {
    pg.deny('DEEPSHIP BLOCK: ' + currentState + ' does not allow ' + kind + ' (' + targetAbs + '). policy.' + policyKey + '=false.');
    return;
  }

  // ── Session ownership ──────────────────────────────────
  var sessionPath = path.join(root, '.deepship', 'session.json');
  var session = pg.readJson(sessionPath);
  if (session && session.owner_worktree) {
    var ownerNorm = pg.normalize(session.owner_worktree);
    var cwdNorm = pg.normalize(cwd);
    var myGen = state.session_started_at || '';
    var ownerGen = session.owner_started_at || '';
    var generationMismatch = myGen && ownerGen && myGen !== ownerGen;
    if (ownerNorm !== cwdNorm || generationMismatch) {
      var reason = generationMismatch
        ? 'session replaced — your session started at ' + myGen + ', owner started at ' + ownerGen
        : 'not session owner. Owner worktree: ' + session.owner_worktree + ', current: ' + cwd;
      pg.deny('DEEPSHIP BLOCK: ' + reason);
      return;
    }
  }

  // ── EXECUTE/REPAIR: work unit boundary ─────────────────
  if (kind === 'code_write' && (currentState === 'EXECUTE' || currentState === 'REPAIR')) {
    if (pg.isMetadataWrite(targetAbs, root)) {
      pg.deny('DEEPSHIP BLOCK: EXECUTE/REPAIR cannot directly edit DEEPSHIP metadata; use RECORD.');
      return;
    }

    var workUnits = pg.readJson(workUnitsPath);
    var currentWuId = state.current_work_unit;
    var units = Array.isArray(workUnits && workUnits.work_units) ? workUnits.work_units : [];
    var currentWu = null;
    for (var i = 0; i < units.length; i++) {
      if (units[i].id === currentWuId) { currentWu = units[i]; break; }
    }

    if (!currentWu) {
      pg.deny('DEEPSHIP BLOCK: no current_work_unit found; PLAN_STEP must create/select a work unit before code edits.');
      return;
    }

    if (!bg.allowedByWorkUnit(targetAbs, root, currentWu)) {
      pg.deny('DEEPSHIP BLOCK: target is outside current work unit files_allowed: ' + targetAbs);
    }
  }
}

main();
