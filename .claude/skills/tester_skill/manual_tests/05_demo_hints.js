// Stage 5 of docs/integration-test-manual.md — Demo hint loop, one demo user per game:
//   5.1 launch demo user  5.2 join <game>_demo league
//   5.3 submit invalid code (per the manual's per-game table) -> hint becomes available
//   5.4 Get Hint (without editing) -> read hint -> restore valid code -> submit
//   5.5 record hint content for the feedback sheet, logout, next game
//
// Local dev gate (.env): SUBMISSIONS_BETWEEN_HINTS=1, HINT_COOLDOWN_SECONDS=0 —
// a hint is available after the first failed submission.
// Hint contents are appended to the state file under `hintResults`, and each
// hint panel is screenshotted to /tmp/agent_games_hint_<game>.png.
//   NODE_PATH="$HOME/.agent-games-playwright/node_modules" node .claude/skills/tester_skill/manual_tests/05_demo_hints.js
const {
  BASE, saveState, launchPage, collectToasts, waitForToast, dismissToasts,
  setMonacoValue, getMonacoValue, submitCode, finish,
} = require('./_helpers');

const SALT = Math.floor(1000 + Math.random() * 9000);

// Invalid edits from the manual's Stage-5 table, anchored to exact starter-code
// lines so drift in the starter code fails loudly instead of testing the wrong thing.
//
// KNOWN MANUAL/APP MISMATCH: three engines silently tolerate the manual's
// "invalid" return instead of failing validation —
//   greedy_pig: anything != "bank" is treated as continue (exceptions -> "bank")
//   prisoners_dilemma: anything not in [defect, collude] -> "collude"
//   arena_champions: invalid action -> role default with a feedback line
// For those, `tolerated` verifies the silent acceptance each run, then the
// hint flow is driven by `find`/`bad` breaking the def line's colon (a syntax
// error — the manual's listed alternative failure).
const GAMES = [
  { game: 'greedy_pig', user: `pig${SALT}`,
    tolerated: { find: 'return decision', bad: "return 'hoard'" },
    find: 'def make_decision(self, game_state):', bad: 'def make_decision(self, game_state)' },
  { game: 'prisoners_dilemma', user: `pd${SALT}`,
    tolerated: { find: 'return decision', bad: "return 'betray'" },
    find: 'def make_decision(self, game_state):', bad: 'def make_decision(self, game_state)' },
  { game: 'lineup4', user: `l4${SALT}`,
    find: 'return random.choice(game_state["possible_moves"]) # fallback to random move', bad: "return '99Z'" },
  { game: 'hearts', user: `hrt${SALT}`,
    find: 'return random.choice(legal_moves)  # fallback to random legal card', bad: "return 'ZZ'" },
  { game: 'ohhell', user: `oh${SALT}`,
    find: 'return random.choice(legal_moves)  # fallback to random legal card', bad: "return 'ZZ'" },
  { game: 'thirteen', user: `t13${SALT}`,
    find: 'return random.choice(legal_moves)  # fallback: a random legal combo (or pass)', bad: "return ['ZZ']" },
  { game: 'arena_champions', user: `arena${SALT}`,
    tolerated: { find: "return random.choice(['attack', 'big_attack', 'precise_attack'])", bad: "return 'flee'" },
    find: 'def make_combat_decision(self, opponent_stats, turn, your_role, last_opponent_action=None):',
    bad: 'def make_combat_decision(self, opponent_stats, turn, your_role, last_opponent_action=None)' },
];

async function runGame(page, observed, spec) {
  console.log(`\n=== ${spec.game} (demo user ${spec.user}) ===`);

  // 5.1 launch a demo user
  await collectToasts(page, observed); // page.goto resets the toast collector
  await page.goto(`${BASE}/Demo`, { waitUntil: 'domcontentloaded' });
  await page.fill('input[placeholder^="Enter a team name"]', spec.user);
  await page.click('button:has-text("Launch Demo Now")');
  await page.waitForURL('**/AgentLeagueSignUp', { timeout: 30000 });
  await page.waitForSelector('text=DEMO MODE', { timeout: 15000 });
  console.log('[5.1] demo session started (DEMO MODE banner shown)');

  // 5.2 join this game's demo league
  const box = page.locator(`input[name="${spec.game}_demo"]`);
  await box.waitFor({ timeout: 20000 });
  await box.check();
  await page.click('button:has-text("Join League")');
  await page.waitForURL('**/AgentSubmission', { timeout: 30000 });
  await page.waitForSelector(`text=LEAGUE: ${spec.game}_demo`, { timeout: 20000 });
  console.log(`[5.2] joined ${spec.game}_demo`);

  // 5.3 submit invalid code
  const starter = await getMonacoValue(page);
  if (!starter.includes(spec.find)) {
    throw new Error(`${spec.game}: starter code does not contain the manual's target line: ${spec.find}`);
  }

  let toleratedNote = null;
  if (spec.tolerated) {
    // The manual claims this edit fails at runtime; the engine actually
    // tolerates it. Verify that silent acceptance, then fall through to the
    // syntax-error variant for the hint flow.
    if (!starter.includes(spec.tolerated.find)) {
      throw new Error(`${spec.game}: starter code does not contain the manual's target line: ${spec.tolerated.find}`);
    }
    await setMonacoValue(page, starter.replace(spec.tolerated.find, spec.tolerated.bad));
    const toleratedSub = await submitCode(page);
    if (toleratedSub.ok) {
      toleratedNote = `manual's invalid edit "${spec.tolerated.bad}" PASSED validation (engine tolerates it); used a syntax error instead`;
      observed.notes = observed.notes || [];
      observed.notes.push(`${spec.game}: ${toleratedNote}`);
      console.log(`[5.3-pre] FINDING confirmed: ${toleratedNote}`);
    } else {
      // Engine behavior changed — the manual's edit now fails after all.
      observed.notes = observed.notes || [];
      observed.notes.push(`${spec.game}: manual's edit "${spec.tolerated.bad}" now FAILS validation (engine tolerance changed?)`);
      console.log(`[5.3-pre] NOTE: manual's edit now fails validation: ${(toleratedSub.body.detail || '').slice(0, 120)}`);
    }
  }

  await setMonacoValue(page, starter.replace(spec.find, spec.bad));
  let badSub = await submitCode(page);
  if (badSub.ok) throw new Error(`${spec.game}: invalid submission unexpectedly passed validation`);
  if (!badSub.body.hint_available) {
    // KNOWN OFF-BY-ONE: hint_available is computed before the attempt is
    // recorded (user_router), and hint_service returns False on an empty
    // history — so a team's FIRST submission never advertises a hint, despite
    // the manual's "available after your first submission". The second
    // identical failure must advertise it.
    observed.notes = observed.notes || [];
    observed.notes.push(`${spec.game}: first failed submission returned hint_available=false (off-by-one); retrying`);
    console.log('[5.3] FINDING: hint_available=false on the team\'s first submission (off-by-one); submitting again');
    badSub = await submitCode(page);
    if (badSub.ok) throw new Error(`${spec.game}: invalid submission unexpectedly passed validation on retry`);
    if (!badSub.body.hint_available) {
      throw new Error(`${spec.game}: hint_available still false on second failed submission (HTTP ${badSub.status}: ${JSON.stringify(badSub.body).slice(0, 300)})`);
    }
  }
  await waitForToast(page, 'A hint is now available');
  const hintButton = page.locator('button:has-text("Get Hint")');
  await hintButton.waitFor({ timeout: 15000 });
  console.log(`[5.3] invalid submission rejected: "${(badSub.body.detail || '').slice(0, 120)}..." — Get Hint button appeared`);

  // 5.4 get the hint (without editing first)
  const [hintResp] = await Promise.all([
    page.waitForResponse((r) => r.url().includes('generate_hint=true'), { timeout: 180000 }),
    hintButton.click(),
  ]);
  const hintBody = await hintResp.json().catch(() => ({}));
  const hint = hintBody.hint;
  if (!hint) {
    throw new Error(`${spec.game}: no hint returned (HTTP ${hintResp.status()}: ${JSON.stringify(hintBody).slice(0, 300)})`);
  }
  await page.waitForSelector('text=Something to think about', { timeout: 15000 });
  await dismissToasts(page); // lingering error toasts overlap the hint panel's buttons
  const reveal = page.locator('button:has-text("Reveal full explanation")');
  if (await reveal.count()) {
    await reveal.click();
    await page.waitForSelector('text=Full explanation', { timeout: 10000 });
  }
  await page.screenshot({ path: `/tmp/agent_games_hint_${spec.game}.png`, fullPage: false });
  console.log(`[5.4] hint (priority ${hint.priority}, line ${hint.line_number}): ${hint.small_hint}`);
  await page.click('button[aria-label="Close hint"]');

  // implement the fix: restore the starter code's known-valid return
  await setMonacoValue(page, starter);
  const goodSub = await submitCode(page);
  if (!goodSub.ok || goodSub.body.submission_id == null) {
    throw new Error(`${spec.game}: valid resubmission failed (HTTP ${goodSub.status}: ${JSON.stringify(goodSub.body).slice(0, 300)})`);
  }
  console.log(`[5.4b] valid resubmission accepted (id=${goodSub.body.submission_id})`);

  // 5.5 logout; hint content is recorded by the caller
  await collectToasts(page, observed);
  await page.click('button:has-text("Logout")');
  await page.waitForURL('**/AgentLogin', { timeout: 15000 });
  console.log('[5.5] logged out');

  return {
    game: spec.game,
    demo_user: spec.user,
    invalid_edit: spec.bad,
    tolerated_note: toleratedNote,
    rejection_detail: badSub.body.detail,
    hint: {
      priority: hint.priority,
      line_number: hint.line_number,
      quoted_line: hint.quoted_line,
      small_hint: hint.small_hint,
      big_hint: hint.big_hint,
    },
    valid_resubmission_ok: true,
  };
}

(async () => {
  const { browser, page, observed } = await launchPage();
  const hintResults = [];
  try {
    for (const spec of GAMES) {
      hintResults.push(await runGame(page, observed, spec));
    }
    saveState({ hintResults });
    console.log('\n=== hint summary ===');
    for (const r of hintResults) {
      console.log(`${r.game}: line ${r.hint.line_number} — ${r.hint.small_hint}`);
    }
    await finish(page, browser, observed, { name: 'STAGE5' });
  } catch (err) {
    saveState({ hintResults });
    await finish(page, browser, observed, { name: 'STAGE5', failure: err });
  }
})();
