// Stage 3 of docs/integration-test-manual.md — Teams ×3:
//   3.1 sign up via the Stage-2 signup URL (credentials modal must appear)
//   3.2 three submissions: starter code (valid), threshold variant (valid),
//       `import os` prepended (must fail the AST safety check)
//       + My Submissions history check
//   3.3 (Team 1 only) one tutorial exercise end-to-end: overview -> "Add Up
//       the Scoreboard" (#4 of 10) -> starter fails 0/5 -> fix passes 5/5 ->
//       broken code (renamed entry function) 400s -> overview shows
//       Completed / 1 of 10.
//       PREREQUISITES: the tutorial must be seeded
//         (docker compose exec api python -m backend.scripts.seed_tutorial)
//       AND attached to the league — Stage 2.3 attaches it.
//   3.4 logout
//
// Reads signupUrl from the state file written by 02_institution_league.js;
// writes the team credentials back for Stage 4.
//   NODE_PATH="$HOME/.agent-games-playwright/node_modules" node .claude/skills/tester_skill/manual_tests/03_team_submissions.js
const {
  BASE, loadState, saveState, launchPage, waitForToast, dismissToasts,
  setMonacoValue, getMonacoValue, submitCode, finish,
} = require('./_helpers');

// Names carry the run suffix so re-runs don't collide with existing teams.
const teamDefs = (run) => [
  { name: `alpha${run}`, password: 'AlphaPass1' },
  { name: `bravo${run}`, password: 'BravoPass1' },
  { name: `charl${run}`, password: 'CharliePass1' },
];

// 3.3 (Team 1 only) — one tutorial exercise per the manual, using seeded
// exercise #4 "Add Up the Scoreboard" (total_banked over the banked_money
// dict, 5 tests). Submission outcomes are asserted from the
// /tutorial/submit-exercise response body (200 with passed/test_results;
// 400 detail when the code never produces results), mirroring how agent
// submissions are asserted from /user/submit-agent. There is deliberately
// NO AST safety gate on exercises any more — the slim exercise-worker
// container is the sandbox — so the "rejected" case is code whose entry
// function is missing, not an unauthorized import.
async function runTutorialExercise(page) {
  console.log('\n=== Tutorial exercise (Team 1 only) ===');

  await page.click('nav a:has-text("Tutorial")');
  await page.waitForURL('**/Tutorial', { timeout: 20000 });
  await page.waitForSelector('h1:has-text("Python Foundations for Greedy Pig")', { timeout: 30000 });
  await page.waitForSelector('text=0 of 10 exercises completed', { timeout: 15000 });
  console.log('[3.3] overview loaded: 10 exercises, 0 of 10 completed');

  await page.click('li button:has-text("Add Up the Scoreboard")');
  await page.waitForSelector('button:has-text("Problem Description")', { timeout: 30000 });
  await page.waitForSelector('text=4. Add Up the Scoreboard', { timeout: 15000 });
  await page.waitForSelector('text=EXERCISE:', { timeout: 15000 });
  if (await page.locator('button:has-text("Get Hint")').count()) {
    throw new Error('tutorial workspace unexpectedly shows a Get Hint button (hints are agent-submission only)');
  }
  console.log('[3.3] exercise workspace open (Problem Description, footer EXERCISE label, no Get Hint)');

  const starter = await getMonacoValue(page);
  if (!starter.includes('def total_banked(banked_money):')) {
    throw new Error('exercise starter code no longer defines total_banked(banked_money)');
  }
  const PASS_LINE = 'pass  # Replace this line with your code';
  if (!starter.includes(PASS_LINE)) {
    throw new Error(`exercise starter code no longer contains the line the manual says to replace: ${PASS_LINE}`);
  }

  // Submission 1 — starter as-is: runs fine but every test must fail (returns None)
  const sub1 = await submitCode(page, 120000, '/tutorial/submit-exercise');
  if (!sub1.ok || sub1.body.passed !== false || (sub1.body.test_results || []).length !== 5) {
    throw new Error(`starter submission should be 200 with 5 failing tests but got HTTP ${sub1.status}: ${JSON.stringify(sub1.body).slice(0, 300)}`);
  }
  await page.waitForSelector('text=0 of 5 tests passed', { timeout: 15000 });
  console.log('[3.3] starter submission: 0 of 5 tests passed (as expected)');

  // Submission 2 — the fix: all tests must pass
  await setMonacoValue(page, starter.replace(PASS_LINE, 'return sum(banked_money.values())'));
  const sub2 = await submitCode(page, 120000, '/tutorial/submit-exercise');
  if (!sub2.ok || sub2.body.passed !== true) {
    throw new Error(`fixed submission should pass all tests but got HTTP ${sub2.status}: ${JSON.stringify(sub2.body).slice(0, 300)}`);
  }
  await page.waitForSelector('text=All 5 tests passed', { timeout: 15000 });
  console.log('[3.3] fixed submission: all 5 tests passed');

  // Submission 3 — code that never produces test results must 400 with the
  // worker's message (recorded without code, like failed agent validation).
  // Renaming the entry function gives a deterministic message.
  await setMonacoValue(page, starter.replace('def total_banked(', 'def total_banked_typo('));
  const sub3 = await submitCode(page, 120000, '/tutorial/submit-exercise');
  if (sub3.ok) throw new Error('broken exercise submission (renamed entry function) unexpectedly passed');
  const detail = sub3.body.detail || '';
  if (!detail.includes("Your code must define a function named 'total_banked'")) {
    throw new Error(`unexpected exercise rejection message: HTTP ${sub3.status} "${detail}"`);
  }
  console.log(`[3.3] broken submission correctly rejected: "${detail}"`);

  // Back to the overview: the exercise is Completed, progress 1 of 10 (a
  // passed run counts even though a rejected attempt came after it). The
  // rejection toast overlaps the panel header in a headless browser —
  // dismiss it first.
  await dismissToasts(page);
  await page.click('button:has-text("All exercises")');
  await page.waitForSelector('text=1 of 10 exercises completed', { timeout: 15000 });
  await page.locator('li button:has-text("Add Up the Scoreboard")')
    .locator('text=Completed').waitFor({ timeout: 15000 });
  console.log('[3.3] overview shows Add Up the Scoreboard as Completed, 1 of 10');
}

async function runTeam(page, observed, signupUrl, team, { withTutorial = false } = {}) {
  console.log(`\n=== Team ${team.name} ===`);

  // 3.1 signup — the /join page opens on its login tab; switch to signup
  // (the tab buttons render once the league info has loaded)
  await page.goto(signupUrl, { waitUntil: 'domcontentloaded' });
  await page.click('button:has-text("Sign up")', { timeout: 20000 });
  await page.fill('#teamName', team.name);
  await page.fill('#password', team.password);
  await page.fill('#confirmPassword', team.password);
  await page.fill('#schoolName', 'Test School');
  await page.click('button:has-text("Sign Up & Join League")');
  await page.waitForSelector('h2:has-text("SAVE YOUR CREDENTIALS NOW!")', { timeout: 15000 });
  await page.click('button:has-text("I\'ve Saved My Credentials")');
  await waitForToast(page, 'Signed up and joined league successfully!');
  await page.waitForURL('**/AgentSubmission', { timeout: 20000 });
  console.log('[3.1] signed up, landed on /AgentSubmission');

  // 3.2a submission 1 — starter code unchanged (valid)
  const starter = await getMonacoValue(page);
  const sub1 = await submitCode(page);
  if (!sub1.ok || sub1.body.submission_id == null) {
    throw new Error(`submission 1 (starter) should pass but got HTTP ${sub1.status}: ${JSON.stringify(sub1.body).slice(0, 300)}`);
  }
  console.log(`[3.2a] valid starter submission ok (id=${sub1.body.submission_id})`);

  // 3.2b submission 2 — bank at a threshold (valid)
  const RANDOM_LINE = "decision = random.choice(['continue', 'bank'])";
  if (!starter.includes(RANDOM_LINE)) {
    throw new Error(`starter code no longer contains the line the manual says to replace: ${RANDOM_LINE}`);
  }
  await setMonacoValue(page, starter.replace(RANDOM_LINE, "decision = 'bank' if my_unbanked >= 20 else 'continue'"));
  const sub2 = await submitCode(page);
  if (!sub2.ok || sub2.body.submission_id == null) {
    throw new Error(`submission 2 (threshold) should pass but got HTTP ${sub2.status}: ${JSON.stringify(sub2.body).slice(0, 300)}`);
  }
  console.log(`[3.2b] valid threshold submission ok (id=${sub2.body.submission_id})`);

  // 3.2c submission 3 — disallowed import (must fail the AST safety check)
  await setMonacoValue(page, 'import os\n' + starter);
  const sub3 = await submitCode(page);
  if (sub3.ok) throw new Error('submission 3 (import os) unexpectedly passed validation');
  const detail = sub3.body.detail || '';
  if (!detail.includes('Agent code is not safe: Unauthorized import: os')) {
    throw new Error(`unexpected rejection message: HTTP ${sub3.status} "${detail}"`);
  }
  console.log(`[3.2c] invalid submission correctly rejected: "${detail}"`);

  // My Submissions history is intentionally code-only: failed attempts are
  // recorded as metadata (for rate limiting and hint rationing) but store no
  // code row, so only the 2 valid submissions appear here — assert 2.
  await page.click('button:has-text("My Submissions")');
  const modal = page.locator('div.fixed:has(h2:has-text("My Submissions"))');
  await modal.waitFor({ timeout: 15000 });
  await modal.locator('text=Loading…').waitFor({ state: 'detached', timeout: 15000 }).catch(() => {});
  await modal.locator('ul > li').first().waitFor({ timeout: 15000 });
  const historyCount = await modal.locator('ul > li').count();
  console.log(`[3.2] My Submissions lists ${historyCount} entries (the 2 valid submissions; failed attempts are metadata-only by design)`);
  if (historyCount !== 2) {
    throw new Error(`My Submissions shows ${historyCount} entries; expected the 2 valid submissions`);
  }
  await modal.locator('div.border-t button:has-text("Close")').click();
  await modal.waitFor({ state: 'detached', timeout: 10000 });

  // 3.3 tutorial exercise — manual says Team 1 only (progress is per-team)
  if (withTutorial) {
    await runTutorialExercise(page);
  }

  // 3.4 logout
  await page.click('button:has-text("Logout")');
  await page.waitForURL('**/AgentLogin', { timeout: 15000 });
  console.log('[3.4] logged out -> /AgentLogin');
}

(async () => {
  const state = loadState();
  if (!state.signupUrl) throw new Error('No signupUrl in state file — run 02_institution_league.js first');

  const teams = teamDefs(state.run ?? Math.floor(1000 + Math.random() * 9000));
  const { browser, page, observed } = await launchPage();
  try {
    for (const [i, team] of teams.entries()) {
      await runTeam(page, observed, state.signupUrl, team, { withTutorial: i === 0 });
    }
    saveState({ teams });
    await finish(page, browser, observed, { name: 'STAGE3' });
  } catch (err) {
    await finish(page, browser, observed, { name: 'STAGE3', failure: err });
  }
})();
