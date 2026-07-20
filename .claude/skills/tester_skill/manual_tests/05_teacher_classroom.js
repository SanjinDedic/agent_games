// Script 05 — Teacher classroom setup (CLASSROOM flow). Mirror of
// 02_institution_league.js for a teacher account (is_teacher=true): same
// routes and endpoints, but every user-visible label switches to
// classroom/student wording (frontend/src/AgentGames/Shared/terminology.js).
//   5.1 login via /Teacher ("Teacher Login" heading, "Account Name:" label)
//       with the teacher credentials from Stage 1; navbar must show
//       "Classroom Management" / "Student Section", never league/team labels
//   5.2 create a greedy_pig classroom ("Create Classroom" button,
//       "Classroom Created Successfully" modal), capture + copy the join URL
//   5.3 attach the seeded tutorial to the classroom (students only see
//       attached tutorials — script 06's Tutorial steps are empty without it)
//   5.4 logout -> /Teacher (teacher accounts return to the teacher login)
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
    await page.waitForURL('**/InstitutionTeam', { timeout: 20000 });
    // Wording guard: a teacher account gets classroom/student labels.
    await page.waitForSelector('nav a:has-text("Classroom Management")', { timeout: 15000 });
    await page.waitForSelector('nav a:has-text("Student Section")', { timeout: 15000 });
    if (await page.locator('nav a:has-text("League Management"), nav a:has-text("Team Section")').count()) {
      throw new Error('teacher navbar shows league/team wording — terminology switch regressed');
    }
    console.log('[5.1] teacher logged in -> /InstitutionTeam (classroom/student wording confirmed)');

    // 5.2 create the classroom (expiry left blank = 24h default; school league unchecked)
    await page.click('a:has-text("Classroom Management")');
    await page.waitForURL('**/InstitutionLeague', { timeout: 15000 });
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
    await page.waitForSelector('h4:has-text("Classroom Created Successfully")', { timeout: 15000 });

    const signupUrl = await page
      .locator('h4:has-text("Classroom Created Successfully") ~ div input[readonly], h4:has-text("Classroom Created Successfully") >> xpath=../descendant::input[@readonly]')
      .first()
      .inputValue();
    if (!/\/join\/.+/.test(signupUrl)) throw new Error(`Classroom join URL looks wrong: "${signupUrl}"`);
    console.log(`[5.2] classroom created: ${classroomName}`);
    console.log(`      join URL: ${signupUrl}`);

    // copy-icon click should toast (same behavior as the league flow)
    await page.locator('button[title="Copy to clipboard"]').last().click();
    await waitForToast(page, 'Signup URL copied to clipboard!');
    const clipboard = await page.evaluate(() => navigator.clipboard.readText()).catch(() => null);
    if (clipboard !== signupUrl) console.warn(`  NOTE: clipboard content mismatch: ${clipboard}`);

    saveState({
      classroomName,
      classroomSignupUrl: signupUrl,
      classroomSignupToken: signupUrl.split('/join/')[1],
      classroomCreateResponse: createBody,
    });

    // Dismiss the success modal so its overlay doesn't block further clicks.
    await modal.locator('button:has-text("Done")').click();
    await modal.waitFor({ state: 'detached', timeout: 10000 });

    // 5.3 attach the seeded tutorial: select the classroom card, tick the
    // tutorial in the Tutorials section, save. The runner seeds the tutorial
    // before Stage 1, so it exists in the library but is not yet attached
    // (the seed only auto-attaches to leagues existing at seed time).
    await page.click(`h3:has-text("${classroomName}")`);
    await page.waitForSelector('h3:has-text("Tutorials")', { timeout: 15000 });
    const tutorialLabel = page.locator('label:has-text("Python Foundations for Greedy Pig")');
    await tutorialLabel.waitFor({ timeout: 15000 });
    await tutorialLabel.locator('input[type="checkbox"]').check();
    await page.click('button:has-text("Save Tutorials")');
    // Backend copy: this toast says "league" even for classrooms.
    await waitForToast(page, `Tutorials updated for league '${classroomName}'`);
    console.log('[5.3] tutorial attached to classroom');

    // 5.4 logout — teacher accounts land back on /Teacher, not /Institution
    await page.click('button:has-text("Logout")');
    await page.waitForURL('**/Teacher', { timeout: 15000 });
    console.log('[5.4] logged out -> /Teacher');

    await finish(page, browser, observed, { name: 'STAGE5' });
  } catch (err) {
    await finish(page, browser, observed, { name: 'STAGE5', failure: err });
  }
})();
