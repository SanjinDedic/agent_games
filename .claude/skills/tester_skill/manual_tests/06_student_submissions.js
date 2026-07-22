// Script 06 — Students ×2 (CLASSROOM flow). Mirror of 03_team_submissions.js
// against the classroom created by 05_teacher_classroom.js: same routes and
// endpoints, but every user-visible label must use classroom/student wording
// ("Student Name", "Sign Up & Join Classroom", STUDENT:/CLASSROOM: footer).
//   6.1 sign up via the classroom join URL (credentials modal must appear);
//       land on /TeamHome with the "You're in the ... classroom" copy
//   6.2 three submissions: starter code (valid), threshold variant (valid),
//       `import os` prepended (must fail the AST safety check)
//       + My Submissions history check
//   6.3 (Student 1 only) one tutorial exercise end-to-end, exactly as in
//       Stage 3.3 but with the STUDENT: footer label: starter fails 0/5 ->
//       fix passes 5/5 -> broken code 400s -> overview Completed / 1 of 10.
//       PREREQUISITES: tutorial seeded AND attached to the classroom (05
//       attaches it). Tutorial progress is per-student, so this classroom
//       student starts at 0 of 10 even after Stage 3 ran.
//   6.4 logout
//
// Known app copy that stays "league" even for students (hardcoded in
// DirectClassicSignup): the signup toast is
// "Signed up and joined league successfully!".
//
// Reads classroomSignupUrl/classroomName from the state file written by
// 05_teacher_classroom.js; writes the student credentials back as `students`.
//   NODE_PATH="$HOME/.agent-games-playwright/node_modules" node .claude/skills/tester_skill/manual_tests/06_student_submissions.js
const {
  loadState, saveState, launchPage, waitForToast, dismissToasts,
  setMonacoValue, getMonacoValue, submitCode, finish,
} = require('./_helpers');

// Names carry the run suffix so re-runs don't collide with existing accounts
// (and stay distinct from Stage 3's alpha/bravo/charl teams).
const studentDefs = (run) => [
  { name: `mia${run}`, password: 'MiaPass1' },
  { name: `noah${run}`, password: 'NoahPass1' },
];

// 6.3 (Student 1 only) — same tutorial exercise as Stage 3.3 ("Add Up the
// Scoreboard", #4 of 10) but asserting the classroom wording: the workspace
// footer label is STUDENT:, not TEAM:. Submission outcomes are asserted from
// the /tutorial/submit-exercise response body exactly as in Stage 3.3.
async function runTutorialExercise(page) {
  console.log('\n=== Tutorial exercise (Student 1 only) ===');

  await page.click('nav a:has-text("Tutorial")');
  await page.waitForURL('**/Tutorial', { timeout: 20000 });
  await page.waitForSelector('h1:has-text("Python Foundations for Greedy Pig")', { timeout: 30000 });
  await page.waitForSelector('text=0 of 10 exercises completed', { timeout: 15000 });
  console.log('[6.3] overview loaded: 10 exercises, 0 of 10 completed');

  await page.click('li button:has-text("Add Up the Scoreboard")');
  await page.waitForSelector('button:has-text("Problem Description")', { timeout: 30000 });
  await page.waitForSelector('text=4. Add Up the Scoreboard', { timeout: 15000 });
  await page.waitForSelector('text=STUDENT:', { timeout: 15000 });
  if (await page.locator('span:text-is("TEAM:")').count()) {
    throw new Error('classroom tutorial workspace shows a TEAM: footer label — terminology switch regressed');
  }
  if (await page.locator('button:has-text("Get Hint")').count()) {
    throw new Error('tutorial workspace unexpectedly shows a Get Hint button (hints are agent-submission only)');
  }
  console.log('[6.3] exercise workspace open (Problem Description, footer STUDENT label, no Get Hint)');

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
  console.log('[6.3] starter submission: 0 of 5 tests passed (as expected)');

  // Submission 2 — the fix: all tests must pass
  await setMonacoValue(page, starter.replace(PASS_LINE, 'return sum(banked_money.values())'));
  const sub2 = await submitCode(page, 120000, '/tutorial/submit-exercise');
  if (!sub2.ok || sub2.body.passed !== true) {
    throw new Error(`fixed submission should pass all tests but got HTTP ${sub2.status}: ${JSON.stringify(sub2.body).slice(0, 300)}`);
  }
  await page.waitForSelector('text=All 5 tests passed', { timeout: 15000 });
  console.log('[6.3] fixed submission: all 5 tests passed');

  // Submission 3 — code that never produces test results must 400 with the
  // worker's message (renamed entry function = deterministic message).
  await setMonacoValue(page, starter.replace('def total_banked(', 'def total_banked_typo('));
  const sub3 = await submitCode(page, 120000, '/tutorial/submit-exercise');
  if (sub3.ok) throw new Error('broken exercise submission (renamed entry function) unexpectedly passed');
  const detail = sub3.body.detail || '';
  if (!detail.includes("Your code must define a function named 'total_banked'")) {
    throw new Error(`unexpected exercise rejection message: HTTP ${sub3.status} "${detail}"`);
  }
  console.log(`[6.3] broken submission correctly rejected: "${detail}"`);

  // Back to the overview: Completed, progress 1 of 10 (per-student progress).
  await dismissToasts(page);
  await page.click('button:has-text("All exercises")');
  await page.waitForSelector('text=1 of 10 exercises completed', { timeout: 15000 });
  await page.locator('li button:has-text("Add Up the Scoreboard")')
    .locator('text=Completed').waitFor({ timeout: 15000 });
  console.log('[6.3] overview shows Add Up the Scoreboard as Completed, 1 of 10');
}

async function runStudent(page, observed, state, student, { withTutorial = false } = {}) {
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
  // Known app copy: this toast is hardcoded and still says "league".
  await waitForToast(page, 'Signed up and joined league successfully!');
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

  // 6.3 tutorial exercise — Student 1 only (progress is per-student)
  if (withTutorial) {
    await runTutorialExercise(page);
  }

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
      await runStudent(page, observed, state, student, { withTutorial: i === 0 });
    }
    saveState({ students });
    await finish(page, browser, observed, { name: 'STAGE6' });
  } catch (err) {
    await finish(page, browser, observed, { name: 'STAGE6', failure: err });
  }
})();
