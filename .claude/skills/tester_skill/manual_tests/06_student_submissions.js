// Script 06 — Students ×2 (CLASSROOM flow). Mirror of 03_team_submissions.js
// against the classroom created by 05_teacher_classroom.js: same routes and
// endpoints, but every user-visible label must use classroom/student wording
// ("Student Name", "Sign Up & Join Classroom", STUDENT:/CLASSROOM: footer).
//   6.1 sign up via the classroom join URL (credentials modal must appear);
//       land on /TeamHome with the "You're in the ... classroom" copy
//   6.2 three submissions: starter code (valid), threshold variant (valid),
//       `import os` prepended (must fail the AST safety check)
//       + My Submissions history check + the landing page reading the same
//       three back (agent panel: 2 valid, 2 placement squares, 1 attempt that
//       didn't get past validation)
//   6.4 logout
//
// Terminology note: the signup toast follows the classroom terminology now
// ("Signed up and joined classroom successfully!").
//
// Reads classroomSignupUrl/classroomName from the state file written by
// 05_teacher_classroom.js; writes the student credentials back as `students`.
//   NODE_PATH="$HOME/.agent-games-playwright/node_modules" node .claude/skills/tester_skill/manual_tests/06_student_submissions.js
const {
  loadState, saveState, launchPage, waitForToast, dismissToasts,
  setMonacoValue, getMonacoValue, readAgentPanel,
  submitCode, finish,
} = require('./_helpers');

// Names carry the run suffix so re-runs don't collide with existing accounts
// (and stay distinct from Stage 3's alpha/bravo/charl teams).
const studentDefs = (run) => [
  { name: `mia${run}`, password: 'MiaPass1' },
  { name: `noah${run}`, password: 'NoahPass1' },
];


// 6.2d — the landing page reports the submissions back. The tiles come from
// GET /user/team-data and the placement squares are the same validation
// placements (in the same colours) the teacher's submissions grid shows, so
// this is where the two views are checked against each other.
async function checkLandingPage(page) {
  await page.click('nav a:has-text("Home")');
  await page.waitForURL('**/TeamHome', { timeout: 20000 });

  // readAgentPanel first: the page renders a loading state until
  // /user/team-data resolves, so nothing else can be read before it.
  const panel = await readAgentPanel(page);

  const sections = await page.locator('section > h2').allInnerTexts();
  if (sections[0] !== 'Agent Game') {
    throw new Error(`landing page sections are ${JSON.stringify(sections)}, expected Agent Game first`);
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
  // history modal — this line is the only place a student sees it.
  if (!/^Last submission /.test(panel.activity)) {
    throw new Error(`landing page activity line reads "${panel.activity}", expected a "Last submission …" line`);
  }
  if (!panel.activity.includes("1 attempt didn't get past validation")) {
    throw new Error(`landing page activity line reads "${panel.activity}", expected the 1 failed attempt to be counted`);
  }
  if (panel.nudge) {
    throw new Error('landing page shows the "Stuck on …" nudge after 2 valid submissions (it needs > 10)');
  }
  console.log(`[6.2d] landing page: 2 valid submissions, placements ${JSON.stringify(panel.recent)} ` +
    `(best ${panel.best} of ${panel.fieldSize}), 1 failed attempt counted`);
}

async function runStudent(page, observed, state, student) {
  console.log(`\n=== Student ${student.name} ===`);

  // 6.1 signup — the /join page opens on its login tab; switch to signup.
  // A classroom's join page must use classroom/student wording throughout.
  await page.goto(state.classroomSignupUrl, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('text=Classroom · greedy_pig', { timeout: 20000 });
  await page.click('button:has-text("Sign up")', { timeout: 20000 });
  const nameLabel = (await page.locator('label[for="teamName"]').innerText()).trim();
  if (nameLabel !== 'Student Name') {
    throw new Error(`join page name label is "${nameLabel}", expected "Student Name" on a classroom`);
  }
  await page.fill('#teamName', student.name);
  await page.fill('#password', student.password);
  await page.fill('#confirmPassword', student.password);
  await page.fill('#schoolName', 'Test School');
  await page.click('button:has-text("Sign Up & Join Classroom")');
  await page.waitForSelector('h2:has-text("SAVE YOUR CREDENTIALS NOW!")', { timeout: 15000 });
  await page.click('button:has-text("I\'ve Saved My Credentials")');
  // The signup toast follows the classroom's terminology (DirectClassicSignup
  // renders `Signed up and joined ${T.league} successfully!`).
  await waitForToast(page, 'Signed up and joined classroom successfully!');
  await page.waitForURL('**/TeamHome', { timeout: 20000 });
  await page.waitForSelector(`text=You're in the ${state.classroomName} classroom`, { timeout: 15000 });
  console.log('[6.1] signed up, landed on /TeamHome (classroom wording)');

  // The landing page links to the agent workspace
  await page.click('a:has-text("Open Agent Workspace")');
  await page.waitForURL('**/AgentSubmission', { timeout: 20000 });
  // Workspace footer labels follow the student's classroom terminology.
  await page.waitForSelector('text=STUDENT:', { timeout: 20000 });
  await page.waitForSelector('text=CLASSROOM:', { timeout: 20000 });
  console.log('[6.1] opened the agent workspace from /TeamHome (STUDENT:/CLASSROOM: footer)');

  // 6.2a submission 1 — starter code unchanged (valid)
  const starter = await getMonacoValue(page);
  const sub1 = await submitCode(page);
  if (!sub1.ok || sub1.body.submission_id == null) {
    throw new Error(`submission 1 (starter) should pass but got HTTP ${sub1.status}: ${JSON.stringify(sub1.body).slice(0, 300)}`);
  }
  console.log(`[6.2a] valid starter submission ok (id=${sub1.body.submission_id})`);

  // 6.2b submission 2 — bank at a threshold (valid)
  const RANDOM_LINE = "decision = random.choice(['continue', 'bank'])";
  if (!starter.includes(RANDOM_LINE)) {
    throw new Error(`starter code no longer contains the line the manual says to replace: ${RANDOM_LINE}`);
  }
  await setMonacoValue(page, starter.replace(RANDOM_LINE, "decision = 'bank' if my_unbanked >= 20 else 'continue'"));
  const sub2 = await submitCode(page);
  if (!sub2.ok || sub2.body.submission_id == null) {
    throw new Error(`submission 2 (threshold) should pass but got HTTP ${sub2.status}: ${JSON.stringify(sub2.body).slice(0, 300)}`);
  }
  console.log(`[6.2b] valid threshold submission ok (id=${sub2.body.submission_id})`);

  // 6.2c submission 3 — disallowed import (must fail the AST safety check;
  // agent submissions keep the AST gate regardless of classroom wording)
  await setMonacoValue(page, 'import os\n' + starter);
  const sub3 = await submitCode(page);
  if (sub3.ok) throw new Error('submission 3 (import os) unexpectedly passed validation');
  const detail = sub3.body.detail || '';
  if (!detail.includes('Agent code is not safe: Unauthorized import: os')) {
    throw new Error(`unexpected rejection message: HTTP ${sub3.status} "${detail}"`);
  }
  console.log(`[6.2c] invalid submission correctly rejected: "${detail}"`);

  // My Submissions history: code-only, so just the 2 valid submissions.
  await page.click('button:has-text("My Submissions")');
  const modal = page.locator('div.fixed:has(h2:has-text("My Submissions"))');
  await modal.waitFor({ timeout: 15000 });
  await modal.locator('text=Loading…').waitFor({ state: 'detached', timeout: 15000 }).catch(() => {});
  await modal.locator('ul > li').first().waitFor({ timeout: 15000 });
  const historyCount = await modal.locator('ul > li').count();
  console.log(`[6.2] My Submissions lists ${historyCount} entries (the 2 valid submissions; failed attempts are metadata-only by design)`);
  if (historyCount !== 2) {
    throw new Error(`My Submissions shows ${historyCount} entries; expected the 2 valid submissions`);
  }
  await modal.locator('div.border-t button:has-text("Close")').click();
  await modal.waitFor({ state: 'detached', timeout: 10000 });

  // 6.2d the same three submissions, read back off the landing page
  await checkLandingPage(page);

  // 6.4 logout
  await page.click('button:has-text("Logout")');
  await page.waitForURL('**/AgentLogin', { timeout: 15000 });
  console.log('[6.4] logged out -> /AgentLogin');
}

(async () => {
  const state = loadState();
  if (!state.classroomSignupUrl || !state.classroomName) {
    throw new Error('No classroomSignupUrl in state file — run 05_teacher_classroom.js first');
  }

  const students = studentDefs(state.run ?? Math.floor(1000 + Math.random() * 9000));
  const { browser, page, observed } = await launchPage();
  try {
    for (const [i, student] of students.entries()) {
      await runStudent(page, observed, state, student);
    }
    saveState({ students });
    await finish(page, browser, observed, { name: 'STAGE6' });
  } catch (err) {
    await finish(page, browser, observed, { name: 'STAGE6', failure: err });
  }
})();
