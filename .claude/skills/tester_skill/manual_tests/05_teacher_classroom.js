// Script 05 — Teacher classroom setup (CLASSROOM flow). Mirror of
// 02_institution_league.js for a teacher account (is_teacher=true): same
// routes and endpoints, but every user-visible label switches to
// classroom/student wording (frontend/src/AgentGames/Shared/terminology.js).
//   5.1 login via /Teacher ("Teacher Login" heading, "Account Name:" label)
//       with the teacher credentials from Stage 1; login lands on
//       /InstitutionHome, whose navbar shows "Students" (never "Teams") and
//       whose heading is "Active Classrooms" (never "Active Leagues")
//   5.2 create a greedy_pig classroom from the Home page's "Create New
//       Classroom" card ("Create Classroom" button, "Classroom Created
//       Successfully" modal); capture + copy the join URL
//   5.3 open the new classroom's workspace and attach the seeded tutorial from
//       its Settings tab (students only see attached tutorials — script 06's
//       Tutorial steps are empty without it)
//   5.4 logout -> /Teacher (teacher accounts return to the teacher login)
//
// Post-revamp layout: the old "Classroom Management" navbar page is gone.
// Creation lives on /InstitutionHome (LeagueCreation card + modal); everything
// else about a classroom lives in the /Classroom/:id/:tab workspace opened from
// the Home card.
//
// Known app copy that stays "league" even for teachers (backend message):
// the Save Tutorials toast is "Tutorials updated for league '<name>'".
//
// Reads teacher credentials from the state file written by 01_admin_setup.js;
// writes classroomName / classroomSignupUrl / classroomSignupToken for 06.
//   NODE_PATH="$HOME/.agent-games-playwright/node_modules" node .claude/skills/tester_skill/manual_tests/05_teacher_classroom.js
const {
  BASE, loadState, saveState, launchPage, waitForToast, finish,
} = require('./_helpers');

(async () => {
  const state = loadState();
  if (!state.teacher) throw new Error('No teacher in state file — run 01_admin_setup.js first');
  const classroomName = `Greedy Pig Test Classroom ${state.run}`;

  const { browser, context, page, observed } = await launchPage();
  // The copy-icon click uses navigator.clipboard, which needs explicit permission headless.
  await context.grantPermissions(['clipboard-read', 'clipboard-write'], { origin: BASE });

  try {
    // 5.1 teacher login — same institution-login endpoint, rebranded page
    await page.goto(`${BASE}/Teacher`, { waitUntil: 'domcontentloaded' });
    await page.waitForSelector('h1:has-text("Teacher Login")', { timeout: 15000 });
    const nameLabel = (await page.locator('label[for="institution_name"]').innerText()).trim();
    if (nameLabel !== 'Account Name:') {
      throw new Error(`/Teacher login label is "${nameLabel}", expected "Account Name:"`);
    }
    await page.fill('#institution_name', state.teacher.name);
    await page.fill('#institution_password', state.teacher.password);
    await page.click('button:has-text("Login")');
    await page.waitForURL('**/InstitutionHome', { timeout: 20000 });
    // Wording guard: a teacher account gets classroom/student labels — the
    // navbar shows "Students" (never "Teams") and the home page lists
    // "Active Classrooms" (never "Active Leagues").
    await page.waitForSelector('h2:has-text("Active Classrooms")', { timeout: 15000 });
    await page.waitForSelector('nav a:has-text("Students")', { timeout: 15000 });
    if (await page.locator('nav a:has-text("Teams")').count()) {
      throw new Error('teacher navbar shows team wording — terminology switch regressed');
    }
    console.log('[5.1] teacher logged in -> /InstitutionHome (classroom/student wording confirmed)');

    // 5.2 create the classroom from the Home page's creation card (expiry left
    // blank = 24h default; school league unchecked; no tutorials selected here)
    await page.waitForSelector('h2:has-text("Create New Classroom")', { timeout: 15000 });
    await page.click('button:has-text("Create Classroom")');
    const modal = page.locator('div.fixed.inset-0');
    await modal.locator('#leagueName').fill(classroomName);
    await modal.locator('#gameName').selectOption('greedy_pig');
    const [createResp] = await Promise.all([
      page.waitForResponse((r) => r.url().includes('/institution/league-create'), { timeout: 30000 }),
      modal.locator('button:has-text("Create Classroom")').click(),
    ]);
    const createBody = await createResp.json().catch(() => ({}));
    if (!createResp.ok()) throw new Error(`league-create HTTP ${createResp.status()}: ${JSON.stringify(createBody)}`);
    await waitForToast(page, 'Classroom created successfully!');

    // Post-revamp, the join link is NOT read from the creation modal: creating
    // from Home refetches the page, and that refetch's loading state unmounts the
    // whole creation card (modal included) before its success view can be read.
    // The new classroom is created WITH a join link, so grab it from the
    // classroom's Home card instead (readonly input + "Copy" button).
    const card = page
      .locator('div.rounded-lg.shadow-lg')
      .filter({ has: page.locator(`button[title="Open the ${classroomName} workspace"]`) });
    await card.waitFor({ timeout: 15000 });
    const signupUrl = await card.locator('input[readonly]').inputValue();
    if (!/\/join\/.+/.test(signupUrl)) throw new Error(`Classroom join URL looks wrong: "${signupUrl}"`);
    console.log(`[5.2] classroom created: ${classroomName}`);
    console.log(`      join URL: ${signupUrl}`);

    // The card's Copy button copies the login link (same behavior as the league flow)
    await card.locator('button:has-text("Copy")').click();
    await waitForToast(page, 'Login link copied to clipboard!');
    const clipboard = await page.evaluate(() => navigator.clipboard.readText()).catch(() => null);
    if (clipboard !== signupUrl) console.warn(`  NOTE: clipboard content mismatch: ${clipboard}`);

    saveState({
      classroomName,
      classroomSignupUrl: signupUrl,
      classroomSignupToken: signupUrl.split('/join/')[1],
      classroomCreateResponse: createBody,
    });

    // 5.3 attach the seeded tutorial: open the classroom workspace from its Home
    // card, go to the Settings tab, tick the tutorial in the Tutorials section,
    // save. The runner seeds the tutorial before Stage 1, so it exists in the
    // library but is not yet attached (the seed only auto-attaches to leagues
    // existing at seed time).
    await card.locator(`button[title="Open the ${classroomName} workspace"]`).click();
    await page.waitForURL('**/Classroom/**', { timeout: 15000 });
    await page.click('button:text-is("Settings")');
    await page.waitForSelector('h3:has-text("Tutorials")', { timeout: 15000 });
    const tutorialLabel = page.locator('label:has-text("Python Foundations for Greedy Pig")');
    await tutorialLabel.waitFor({ timeout: 15000 });
    await tutorialLabel.locator('input[type="checkbox"]').check();
    await page.click('button:has-text("Save Tutorials")');
    // Backend copy: this toast says "league" even for classrooms.
    await waitForToast(page, `Tutorials updated for league '${classroomName}'`);
    console.log('[5.3] tutorial attached to classroom via the workspace Settings tab');

    // 5.4 logout — teacher accounts land back on /Teacher, not /Institution
    await page.click('button:has-text("Logout")');
    await page.waitForURL('**/Teacher', { timeout: 15000 });
    console.log('[5.4] logged out -> /Teacher');

    await finish(page, browser, observed, { name: 'STAGE5' });
  } catch (err) {
    await finish(page, browser, observed, { name: 'STAGE5', failure: err });
  }
})();
