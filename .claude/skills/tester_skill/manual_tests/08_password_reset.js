// Script 08 — Team password reset (CLASSROOM flow). Exercises the one-time
// reset link end-to-end against the student created by 06_student_submissions.js:
//   8.1 teacher login via /Teacher -> /InstitutionTeam; click Reset on
//       Student 1's card -> POST /institution/team-password-reset returns a
//       reset_token; modal must use student wording ("Share this link with
//       the student.") and promise "works once and expires in 48 hours";
//       clicking Reset AGAIN issues a different token (regeneration replaces
//       the old one, so a mis-shared link can be invalidated); Copy toasts
//   8.2 the FIRST link is now dead: /reset/<tokenA> shows the
//       invalid-or-expired error (consumed/regenerated/expired/nonexistent
//       links are indistinguishable by design)
//   8.3 the live link: page shows the teacher account name + student name and
//       classroom wording ("your existing student account"); mismatched
//       confirm -> "Passwords do not match" (client-side, nothing sent);
//       matching passwords -> POST /user/reset-team-password 200 with
//       access_token (auto-login), "Password updated" done state, Continue ->
//       /TeamHome with the classroom copy; work kept: the agent workspace's
//       My Submissions still lists stage 6's 2 valid submissions
//   8.4 logout, then the consumed link is dead too: /reset/<tokenB> errors
//   8.5 old password rejected at the classroom join login (team-login !ok),
//       new password logs in -> /TeamHome; logout
//
// Reads teacher (01), classroomSignupUrl/classroomName (05) and students (06)
// from the state file; writes Student 1's new password back so any later
// script using `students` stays correct.
//   NODE_PATH="$HOME/.agent-games-playwright/node_modules" node .claude/skills/tester_skill/manual_tests/08_password_reset.js
const {
  BASE, loadState, saveState, launchPage, waitForToast, finish,
} = require('./_helpers');

(async () => {
  const state = loadState();
  if (!state.teacher) throw new Error('No teacher in state file — run 01_admin_setup.js first');
  if (!state.classroomSignupUrl || !state.classroomName) {
    throw new Error('No classroomSignupUrl in state file — run 05_teacher_classroom.js first');
  }
  if (!state.students?.length) throw new Error('No students in state file — run 06_student_submissions.js first');

  const student = state.students[0];
  const oldPassword = student.password;
  const newPassword = `${oldPassword}Reset9`;

  const { browser, context, page, observed } = await launchPage();
  // The modal's Copy button uses navigator.clipboard, which needs explicit permission headless.
  await context.grantPermissions(['clipboard-read', 'clipboard-write'], { origin: BASE });

  try {
    // 8.1 teacher login (as in 05.1) — lands on /InstitutionTeam, the student list
    await page.goto(`${BASE}/Teacher`, { waitUntil: 'domcontentloaded' });
    await page.fill('#institution_name', state.teacher.name);
    await page.fill('#institution_password', state.teacher.password);
    await page.click('button:has-text("Login")');
    await page.waitForURL('**/InstitutionTeam', { timeout: 20000 });

    // Student 1's card (name + school + Reset/X buttons) inside the table
    const card = page.locator(`td div.bg-ui-lighter:has(span:text-is("${student.name}"))`);
    await card.waitFor({ timeout: 20000 });

    const clickReset = async () => {
      const [resp] = await Promise.all([
        page.waitForResponse((r) => r.url().includes('/institution/team-password-reset') && r.request().method() === 'POST', { timeout: 20000 }),
        card.locator('button:has-text("Reset")').click(),
      ]);
      const body = await resp.json().catch(() => ({}));
      if (!resp.ok() || !body.reset_token) {
        throw new Error(`team-password-reset HTTP ${resp.status()}: ${JSON.stringify(body).slice(0, 300)}`);
      }
      if (body.team_name !== student.name) {
        throw new Error(`reset link generated for "${body.team_name}", expected "${student.name}"`);
      }
      return body.reset_token;
    };

    const tokenA = await clickReset();
    const modal = page.locator('div.fixed:has(h2:has-text("Password reset link"))');
    await modal.locator(`h2:has-text("Password reset link for ${student.name}")`).waitFor({ timeout: 15000 });
    // Teacher wording guard: the share copy must say "student", not "team".
    await modal.locator('text=Share this link with the student.').waitFor({ timeout: 15000 });
    await modal.locator('text=The link works once and expires in 48 hours.').waitFor({ timeout: 15000 });
    const urlA = await modal.locator('input[readonly]').inputValue();
    if (urlA !== `${BASE}/reset/${tokenA}`) {
      throw new Error(`modal shows "${urlA}", expected "${BASE}/reset/${tokenA}"`);
    }
    console.log(`[8.1] reset link generated for ${student.name} (student wording confirmed)`);
    await modal.locator('button:has-text("Close")').click();
    await modal.waitFor({ state: 'detached', timeout: 10000 });

    // Regenerating must mint a fresh token — the first link dies (asserted in 8.2)
    const tokenB = await clickReset();
    if (tokenB === tokenA) throw new Error('regenerating the reset link returned the same token — old links cannot be invalidated');
    await modal.waitFor({ timeout: 15000 });
    await modal.locator('button:has-text("Copy")').click();
    await waitForToast(page, 'Password reset link copied to clipboard!');
    const clipboard = await page.evaluate(() => navigator.clipboard.readText()).catch(() => null);
    if (clipboard !== `${BASE}/reset/${tokenB}`) console.warn(`  NOTE: clipboard content mismatch: ${clipboard}`);
    console.log('[8.1] regenerated: new token differs, Copy toasted');
    await modal.locator('button:has-text("Close")').click();
    await modal.waitFor({ state: 'detached', timeout: 10000 });

    await page.click('button:has-text("Logout")');
    await page.waitForURL('**/Teacher', { timeout: 15000 });

    // 8.2 the replaced link must be indistinguishable from a dead one
    await page.goto(`${BASE}/reset/${tokenA}`, { waitUntil: 'domcontentloaded' });
    await page.waitForSelector('text=This password reset link is invalid or has expired', { timeout: 20000 });
    await page.waitForSelector('a:has-text("Return to home page")', { timeout: 15000 });
    console.log('[8.2] replaced link correctly rejected as invalid/expired');

    // 8.3 the live link: who-is-this-for header + classroom wording
    await page.goto(`${BASE}/reset/${tokenB}`, { waitUntil: 'domcontentloaded' });
    await page.waitForSelector(`h1:has-text("${student.name}")`, { timeout: 20000 });
    await page.waitForSelector(`text=${state.teacher.name}`, { timeout: 15000 });
    await page.waitForSelector('text=Set a new password', { timeout: 15000 });
    // Wording guard: the owning institution is a teacher, so "student account".
    await page.waitForSelector('text=This logs you into your existing student account', { timeout: 15000 });
    console.log('[8.3] reset page shows teacher + student names (student wording confirmed)');

    // Mismatched confirm is caught client-side
    await page.fill('input[name="password"]', newPassword);
    await page.fill('input[name="confirm"]', `${newPassword}typo`);
    await page.click('button:has-text("Set password and log in")');
    await page.waitForSelector('p.text-danger:has-text("Passwords do not match")', { timeout: 15000 });
    console.log('[8.3] mismatched confirm rejected: "Passwords do not match"');

    // Matching passwords: reset + auto-login in one step
    await page.fill('input[name="confirm"]', newPassword);
    const [resetResp] = await Promise.all([
      page.waitForResponse((r) => r.url().includes('/user/reset-team-password') && r.request().method() === 'POST', { timeout: 20000 }),
      page.click('button:has-text("Set password and log in")'),
    ]);
    const resetBody = await resetResp.json().catch(() => ({}));
    if (!resetResp.ok() || !resetBody.access_token || resetBody.team_name !== student.name) {
      throw new Error(`reset-team-password HTTP ${resetResp.status()}: ${JSON.stringify(resetBody).slice(0, 300)}`);
    }
    await page.waitForSelector('text=Password updated', { timeout: 15000 });
    await page.waitForSelector(`text=You're logged in as`, { timeout: 15000 });
    console.log('[8.3] password reset + auto-login ok');

    await page.click('button:has-text("Continue to your workspace")');
    await page.waitForURL('**/TeamHome', { timeout: 20000 });
    await page.waitForSelector(`text=You're in the ${state.classroomName} classroom`, { timeout: 15000 });

    // Work kept: stage 6's 2 valid submissions are still in My Submissions
    await page.click('a:has-text("Open Agent Workspace")');
    await page.waitForURL('**/AgentSubmission', { timeout: 20000 });
    await page.waitForSelector('text=STUDENT:', { timeout: 20000 });
    await page.click('button:has-text("My Submissions")');
    const historyModal = page.locator('div.fixed:has(h2:has-text("My Submissions"))');
    await historyModal.waitFor({ timeout: 15000 });
    await historyModal.locator('text=Loading…').waitFor({ state: 'detached', timeout: 15000 }).catch(() => {});
    await historyModal.locator('ul > li').first().waitFor({ timeout: 15000 });
    const historyCount = await historyModal.locator('ul > li').count();
    if (historyCount !== 2) {
      throw new Error(`My Submissions shows ${historyCount} entries after reset; expected stage 6's 2 — did the reset log into the wrong account?`);
    }
    console.log('[8.3] work kept: My Submissions still lists the 2 stage-6 submissions');
    await historyModal.locator('div.border-t button:has-text("Close")').click();
    await historyModal.waitFor({ state: 'detached', timeout: 10000 });

    // 8.4 the link was consumed by the reset — it must be dead now
    await page.click('button:has-text("Logout")');
    await page.waitForURL('**/AgentLogin', { timeout: 15000 });
    await page.goto(`${BASE}/reset/${tokenB}`, { waitUntil: 'domcontentloaded' });
    await page.waitForSelector('text=This password reset link is invalid or has expired', { timeout: 20000 });
    console.log('[8.4] consumed link correctly rejected as invalid/expired');

    // 8.5 the classroom join login: old password dead, new password works
    await page.goto(state.classroomSignupUrl, { waitUntil: 'domcontentloaded' });
    await page.waitForSelector('text=Classroom · greedy_pig', { timeout: 20000 });
    await page.fill('input[name="name"]', student.name);
    await page.fill('input[name="password"]', oldPassword);
    // The tab header also says "Log in"; the submit button is the w-full one.
    const [oldResp] = await Promise.all([
      page.waitForResponse((r) => r.url().includes('/auth/team-login') && r.request().method() === 'POST', { timeout: 20000 }),
      page.click('button.w-full:has-text("Log in")'),
    ]);
    if (oldResp.ok()) throw new Error('login with the OLD password unexpectedly succeeded after the reset');
    await page.waitForSelector('p.text-danger', { timeout: 15000 });
    console.log(`[8.5] old password correctly rejected (HTTP ${oldResp.status()})`);

    await page.fill('input[name="password"]', newPassword);
    const [newResp] = await Promise.all([
      page.waitForResponse((r) => r.url().includes('/auth/team-login') && r.request().method() === 'POST', { timeout: 20000 }),
      page.click('button.w-full:has-text("Log in")'),
    ]);
    if (!newResp.ok()) throw new Error(`login with the NEW password failed: HTTP ${newResp.status()}`);
    await page.waitForURL('**/TeamHome', { timeout: 20000 });
    console.log('[8.5] new password logs in -> /TeamHome');

    await page.click('button:has-text("Logout")');
    await page.waitForURL('**/AgentLogin', { timeout: 15000 });

    // Keep the state file truthful for anything that reuses `students`.
    const students = state.students.map((s, i) => (i === 0 ? { ...s, password: newPassword } : s));
    saveState({ students, passwordReset: { student: student.name, oldPassword, newPassword } });

    await finish(page, browser, observed, { name: 'STAGE8' });
  } catch (err) {
    await finish(page, browser, observed, { name: 'STAGE8', failure: err });
  }
})();
