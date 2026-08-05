// Stage 3 of docs/integration-test-manual.md — Teams ×3 (COMPETITION flow:
// the join page and workspace must use league/team wording; the
// student/classroom counterpart is 06_student_submissions.js):
//   3.1 sign up via the Stage-2 signup URL (credentials modal must appear)
//   3.2 three submissions: starter code (valid), threshold variant (valid),
//       `import os` prepended (must fail the AST safety check)
//       + My Submissions history check + the landing page reading the same
//       three back (agent panel: 2 valid, 2 placement squares, 1 attempt that
//       didn't get past validation)
//   3.3 (Team 1 only) one tutorial exercise end-to-end: overview -> "Add Up
//       the Scoreboard" (position read off the overview) -> starter fails
//       0/5 -> fix passes 5/5 -> broken code (syntax error) 400s -> overview
//       shows Completed / 1 of <total>.
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
  setMonacoValue, getMonacoValue, readTutorialOverview, readAgentPanel,
  submitCode, finish,
} = require('./_helpers');

const EXERCISE = 'Add Up the Scoreboard';
const TUTORIAL = 'Python Foundations for Greedy Pig';

// Names carry the run suffix so re-runs don't collide with existing teams.
const teamDefs = (run) => [
  { name: `alpha${run}`, password: 'AlphaPass1' },
  { name: `bravo${run}`, password: 'BravoPass1' },
  { name: `charl${run}`, password: 'CharliePass1' },
];

// 3.3 (Team 1 only) — one tutorial exercise per the manual, using the seeded
// exercise "Add Up the Scoreboard" (a top-level-code exercise: total/past_20
// accumulated over the banked_money dict and printed, 5 tests, no entry
// function). Its position and the tutorial's exercise count are read off the
// overview rather than hardcoded — the tutorial is authored content and grows.
// Submission outcomes are asserted from the submit response body (200 with
// passed/test_results; 400 detail when the code never produces results),
// mirroring how agent submissions are asserted from /user/submit-agent.
// Exercises run Pyodide-first in the browser and persist via
// /tutorial/submit-exercise-result — the only exercise endpoint; the server
// never executes exercise code (when Pyodide can't run, the browser calls
// the fallback Lambda's Function URL directly and persists the envelope
// through the same endpoint). The '/tutorial/submit-exercise' substring in
// waitForResponse matches it. There is deliberately NO AST safety gate on
// exercises — the sandbox is the Pyodide worker (or the Lambda) — so the
// "rejected" case is code that never produces results (a syntax error),
// not an unauthorized import.
async function runTutorialExercise(page) {
  console.log('\n=== Tutorial exercise (Team 1 only) ===');

  await page.click('nav a:has-text("Tutorial")');
  await page.waitForURL('**/Tutorial', { timeout: 20000 });
  await page.waitForSelector(`h1:has-text("${TUTORIAL}")`, { timeout: 30000 });
  const overview = await readTutorialOverview(page, EXERCISE);
  if (overview.passed !== 0) {
    throw new Error(`fresh team should start at 0 completed, overview says ${overview.passed}`);
  }
  if (!overview.position) throw new Error(`"${EXERCISE}" is already completed before this stage ran`);
  console.log(`[3.3] overview loaded: ${overview.total} exercises, 0 of ${overview.total} completed ` +
    `("${EXERCISE}" is #${overview.position})`);

  await page.click(`li button:has-text("${EXERCISE}")`);
  await page.waitForSelector('button:has-text("Problem Description")', { timeout: 30000 });
  await page.waitForSelector(`text=${overview.position}. ${EXERCISE}`, { timeout: 15000 });
  await page.waitForSelector('text=TEAM:', { timeout: 15000 });
  if (await page.locator('button:has-text("Get Hint")').count()) {
    throw new Error('tutorial workspace unexpectedly shows a Get Hint button (hints are agent-submission only)');
  }
  console.log('[3.3] exercise workspace open (Problem Description, footer TEAM label, no Get Hint)');

  const starter = await getMonacoValue(page);
  if (!starter.includes('banked_money = {')) {
    throw new Error('exercise starter code no longer sets up the banked_money scoreboard dict');
  }
  const TODO_LINE = '# Your code goes here';
  if (!starter.includes(TODO_LINE)) {
    throw new Error(`exercise starter code no longer contains the line the student replaces: ${TODO_LINE}`);
  }

  // Submission 1 — starter as-is: runs fine (just the dict and comments) but
  // every test must fail (total/past_20 undefined, nothing printed)
  const sub1 = await submitCode(page, 120000, '/tutorial/submit-exercise');
  if (!sub1.ok || sub1.body.passed !== false || (sub1.body.test_results || []).length !== 5) {
    throw new Error(`starter submission should be 200 with 5 failing tests but got HTTP ${sub1.status}: ${JSON.stringify(sub1.body).slice(0, 300)}`);
  }
  await page.waitForSelector('text=0 of 5 tests passed', { timeout: 15000 });
  console.log('[3.3] starter submission: 0 of 5 tests passed (as expected)');

  // Submission 2 — the fix: all tests must pass
  const FIX = [
    'total = 0',
    'past_20 = 0',
    'for money in banked_money.values():',
    '    total = total + money',
    '    if money >= 20:',
    '        past_20 = past_20 + 1',
    '',
    'print(f"Total banked: {total}")',
    'print(f"Players past 20: {past_20}")',
  ].join('\n');
  await setMonacoValue(page, starter.replace(TODO_LINE, FIX));
  const sub2 = await submitCode(page, 120000, '/tutorial/submit-exercise');
  if (!sub2.ok || sub2.body.passed !== true) {
    throw new Error(`fixed submission should pass all tests but got HTTP ${sub2.status}: ${JSON.stringify(sub2.body).slice(0, 300)}`);
  }
  await page.waitForSelector('text=All 5 tests passed', { timeout: 15000 });
  console.log('[3.3] fixed submission: all 5 tests passed');

  // Submission 3 — code that never produces test results must 400 with the
  // harness's message (recorded without code, like failed agent validation).
  // The exercise is top-level code (no entry function), so a syntax error is
  // the deterministic no-results case — same message from Pyodide and the
  // Celery fallback (harness parity).
  await setMonacoValue(page, starter + '\nthis is not python\n');
  const sub3 = await submitCode(page, 120000, '/tutorial/submit-exercise');
  if (sub3.ok) throw new Error('broken exercise submission (syntax error) unexpectedly passed');
  const detail = sub3.body.detail || '';
  if (!detail.includes('Your code failed to run before any tests started.')) {
    throw new Error(`unexpected exercise rejection message: HTTP ${sub3.status} "${detail}"`);
  }
  console.log(`[3.3] broken submission correctly rejected: "${detail}"`);

  // Back to the overview: the exercise is Completed, progress 1 of <total> (a
  // passed run counts even though a rejected attempt came after it). The
  // rejection toast overlaps the panel header in a headless browser —
  // dismiss it first.
  await dismissToasts(page);
  await page.click('button:has-text("All exercises")');
  await page.waitForSelector(`text=1 of ${overview.total} exercises completed`, { timeout: 15000 });
  await page.locator(`li button:has-text("${EXERCISE}")`)
    .locator('text=Completed').waitFor({ timeout: 15000 });
  console.log(`[3.3] overview shows ${EXERCISE} as Completed, 1 of ${overview.total}`);

  // The landing page counts the same pass on its tutorial card, under the
  // agent panel — same number, two places, one backend call (/user/team-data).
  await page.click('nav a:has-text("Home")');
  await page.waitForURL('**/TeamHome', { timeout: 20000 });
  const tutorialCard = page.locator('section button').filter({ hasText: TUTORIAL }).first();
  await tutorialCard.waitFor({ timeout: 15000 });
  const cardText = (await tutorialCard.innerText()).replace(/\s+/g, ' ');
  if (!cardText.includes(`1 of ${overview.total} exercises completed`)) {
    throw new Error(`landing page tutorial card reads "${cardText}", expected 1 of ${overview.total} completed`);
  }
  console.log(`[3.3] landing page tutorial card agrees: 1 of ${overview.total} completed`);
}

// 3.2d — the landing page reports the submissions back. The tiles come from
// GET /user/team-data and the placement squares are the same validation
// placements (in the same colours) the institution's submissions grid shows,
// so this is where the two views are checked against each other.
async function checkLandingPage(page) {
  await page.click('nav a:has-text("Home")');
  await page.waitForURL('**/TeamHome', { timeout: 20000 });

  // readAgentPanel first: the page renders a loading state until
  // /user/team-data resolves, so nothing else can be read before it.
  const panel = await readAgentPanel(page);

  // The agent game leads the page; the tutorials sit under it.
  const sections = await page.locator('section > h2').allInnerTexts();
  if (sections[0] !== 'Agent Game') {
    throw new Error(`landing page sections are ${JSON.stringify(sections)}, expected Agent Game first`);
  }
  // Competition wording: a team's courses stay "Tutorials" (script 06 asserts
  // the teacher-account counterpart, "Short Courses").
  if (!sections.includes('Tutorials')) {
    throw new Error(`landing page sections are ${JSON.stringify(sections)}, expected a Tutorials section`);
  }

  if (panel.validSubmissions !== 2) {
    throw new Error(`landing page shows ${panel.validSubmissions} valid submissions, expected 2`);
  }
  if (panel.recent.length !== 2) {
    throw new Error(`landing page shows ${panel.recent.length} recent placements, expected 2 (one per valid submission)`);
  }
  if (panel.best !== Math.min(...panel.recent)) {
    throw new Error(`best placement is ${panel.best} but the recent placements are ${JSON.stringify(panel.recent)}`);
  }
  if (!panel.fieldSize || panel.best > panel.fieldSize) {
    throw new Error(`placement ${panel.best} of field size ${panel.fieldSize} is not a possible reading`);
  }
  if (panel.reachedFirst !== (panel.best === 1)) {
    throw new Error(`REACHED 1ST badge ${panel.reachedFirst ? 'shown' : 'missing'} with a best placement of ${panel.best}`);
  }
  // The AST-rejected submission is metadata-only, so it never reaches the
  // history modal — this line is the only place a team sees it.
  if (!/^Last submission /.test(panel.activity)) {
    throw new Error(`landing page activity line reads "${panel.activity}", expected a "Last submission …" line`);
  }
  if (!panel.activity.includes("1 attempt didn't get past validation")) {
    throw new Error(`landing page activity line reads "${panel.activity}", expected the 1 failed attempt to be counted`);
  }
  if (panel.nudge) {
    throw new Error('landing page shows the "Stuck on …" nudge after 2 valid submissions (it needs > 10)');
  }
  console.log(`[3.2d] landing page: 2 valid submissions, placements ${JSON.stringify(panel.recent)} ` +
    `(best ${panel.best} of ${panel.fieldSize}), 1 failed attempt counted`);
}

async function runTeam(page, observed, signupUrl, team, { withTutorial = false } = {}) {
  console.log(`\n=== Team ${team.name} ===`);

  // 3.1 signup — the /join page opens on its login tab; switch to signup
  // (the tab buttons render once the league info has loaded). A competition
  // league's join page must use league/team wording (classroom/student
  // wording is the teacher flow, script 06).
  await page.goto(signupUrl, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('text=League · greedy_pig', { timeout: 20000 });
  await page.click('button:has-text("Sign up")', { timeout: 20000 });
  const nameLabel = (await page.locator('label[for="teamName"]').innerText()).trim();
  if (nameLabel !== 'Team Name') {
    throw new Error(`join page name label is "${nameLabel}", expected "Team Name" on a competition league`);
  }
  await page.fill('#teamName', team.name);
  await page.fill('#password', team.password);
  await page.fill('#confirmPassword', team.password);
  await page.fill('#schoolName', 'Test School');
  await page.click('button:has-text("Sign Up & Join League")');
  await page.waitForSelector('h2:has-text("SAVE YOUR CREDENTIALS NOW!")', { timeout: 15000 });
  await page.click('button:has-text("I\'ve Saved My Credentials")');
  await waitForToast(page, 'Signed up and joined league successfully!');
  await page.waitForURL('**/TeamHome', { timeout: 20000 });
  // Competition wording on the landing page: "competing", not "classroom".
  await page.waitForSelector('text=You\'re competing in', { timeout: 15000 });
  console.log('[3.1] signed up, landed on /TeamHome (competition wording)');

  // The landing page links to the agent workspace
  await page.click('a:has-text("Open Agent Workspace")');
  await page.waitForURL('**/AgentSubmission', { timeout: 20000 });
  // Workspace footer labels come from the same terminology switch.
  await page.waitForSelector('text=TEAM:', { timeout: 20000 });
  await page.waitForSelector('text=LEAGUE:', { timeout: 20000 });
  console.log('[3.1] opened the agent workspace from /TeamHome (TEAM:/LEAGUE: footer)');

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

  // 3.2d the same three submissions, read back off the landing page
  await checkLandingPage(page);

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
