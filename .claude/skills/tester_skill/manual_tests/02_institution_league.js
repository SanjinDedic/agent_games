// Stage 2 of docs/integration-test-manual.md — Institution (COMPETITION flow:
// institution + league + team wording; the teacher/classroom counterpart is
// 05_teacher_classroom.js):
//   2.1 login as the KEPT institution (from Stage 1 state); login lands on
//       /InstitutionHome, whose navbar + copy must use league/team wording
//       (navbar "Teams", home heading "Active Leagues"), never classroom/student
//   2.2 create a greedy_pig league from the Home page's "Create New League"
//       card; capture + copy the signup URL from the success modal
//   2.3 open the new league's workspace and attach the seeded tutorial from
//       its Settings tab (teams only see tutorials attached to their league;
//       creation attaches none here, and Stage 3.3's Tutorial page is empty
//       without this)
//
// Post-revamp layout: the old "League Management" navbar page is gone. Creation
// lives on /InstitutionHome (LeagueCreation card + modal); everything else about
// a league lives in the /Classroom/:id/:tab workspace opened from the Home card.
//
// Reads institution credentials from the state file written by 01_admin_setup.js;
// writes leagueName / signupUrl / signupToken back for Stage 3.
//   NODE_PATH="$HOME/.agent-games-playwright/node_modules" node .claude/skills/tester_skill/manual_tests/02_institution_league.js
const {
  BASE, loadState, saveState, launchPage, waitForToast, finish,
} = require('./_helpers');

(async () => {
  const state = loadState();
  if (!state.institution) throw new Error('No institution in state file — run 01_admin_setup.js first');
  const leagueName = `Greedy Pig Test League ${state.run}`;

  const { browser, context, page, observed } = await launchPage();
  // The copy-icon click uses navigator.clipboard, which needs explicit permission headless.
  await context.grantPermissions(['clipboard-read', 'clipboard-write'], { origin: BASE });

  try {
    // 2.1 institution login -> /InstitutionHome
    await page.goto(`${BASE}/Institution`, { waitUntil: 'domcontentloaded' });
    await page.fill('#institution_name', state.institution.name);
    await page.fill('#institution_password', state.institution.password);
    await page.click('button:has-text("Login")');
    await page.waitForURL('**/InstitutionHome', { timeout: 20000 });
    // Wording guard: a non-teacher institution gets league/team labels — the
    // navbar shows "Teams" (never "Students") and the home page lists
    // "Active Leagues" (never "Active Classrooms").
    await page.waitForSelector('h2:has-text("Active Leagues")', { timeout: 15000 });
    await page.waitForSelector('nav a:has-text("Teams")', { timeout: 15000 });
    if (await page.locator('nav a:has-text("Students")').count()) {
      throw new Error('institution navbar shows student wording — is_teacher leaked into a competition account');
    }
    console.log('[2.1] institution logged in -> /InstitutionHome (league/team wording confirmed)');

    // 2.2 create the league from the Home page's creation card (expiry left
    // blank = 24h default; school league unchecked; no tutorials selected here)
    await page.waitForSelector('h2:has-text("Create New League")', { timeout: 15000 });
    await page.click('button:has-text("Create League")');
    const modal = page.locator('div.fixed.inset-0');
    await modal.locator('#leagueName').fill(leagueName);
    await modal.locator('#gameName').selectOption('greedy_pig');
    const [createResp] = await Promise.all([
      page.waitForResponse((r) => r.url().includes('/institution/league-create'), { timeout: 30000 }),
      modal.locator('button:has-text("Create League")').click(),
    ]);
    const createBody = await createResp.json().catch(() => ({}));
    if (!createResp.ok()) throw new Error(`league-create HTTP ${createResp.status()}: ${JSON.stringify(createBody)}`);
    await waitForToast(page, 'League created successfully!');

    // Post-revamp, the signup link is NOT read from the creation modal: creating
    // from Home refetches the page, and that refetch's loading state unmounts the
    // whole creation card (modal included) before its success view can be read.
    // The new league is created WITH a signup link, so grab it from the league's
    // Home card instead (readonly input + "Copy" button).
    const card = page
      .locator('div.rounded-lg.shadow-lg')
      .filter({ has: page.locator(`button[title="Open the ${leagueName} workspace"]`) });
    await card.waitFor({ timeout: 15000 });
    const signupUrl = await card.locator('input[readonly]').inputValue();
    if (!/\/join\/.+/.test(signupUrl)) throw new Error(`Signup URL looks wrong: "${signupUrl}"`);
    console.log(`[2.2] league created: ${leagueName}`);
    console.log(`      signup URL: ${signupUrl}`);

    // The card's Copy button copies the login link (manual step 2.2.5)
    await card.locator('button:has-text("Copy")').click();
    await waitForToast(page, 'Login link copied to clipboard!');
    const clipboard = await page.evaluate(() => navigator.clipboard.readText()).catch(() => null);
    if (clipboard !== signupUrl) console.warn(`  NOTE: clipboard content mismatch: ${clipboard}`);

    saveState({
      leagueName,
      signupUrl,
      signupToken: signupUrl.split('/join/')[1],
      leagueCreateResponse: createBody,
    });

    // 2.3 attach the seeded tutorial: open the new league's workspace from its
    // Home card, go to the Settings tab, tick the tutorial in the Tutorials
    // section, save. The runner seeds the tutorial before Stage 1, so it exists
    // in the library but is not yet attached to this league (the seed only
    // auto-attaches to leagues existing at seed time).
    await card.locator(`button[title="Open the ${leagueName} workspace"]`).click();
    await page.waitForURL('**/Classroom/**', { timeout: 15000 });
    await page.click('button:text-is("Settings")');
    await page.waitForSelector('h3:has-text("Tutorials")', { timeout: 15000 });
    const tutorialLabel = page.locator('label:has-text("Python Foundations for Greedy Pig")');
    await tutorialLabel.waitFor({ timeout: 15000 });
    await tutorialLabel.locator('input[type="checkbox"]').check();
    await page.click('button:has-text("Save Tutorials")');
    await waitForToast(page, `Tutorials updated for league '${leagueName}'`);
    console.log('[2.3] tutorial attached to league via the workspace Settings tab');

    // Logout to leave a clean session for Stage 3 (manual says either is fine).
    await page.click('button:has-text("Logout")');
    await page.waitForURL('**/Institution', { timeout: 15000 });
    console.log('[2.x] logged out -> /Institution');

    await finish(page, browser, observed, { name: 'STAGE2' });
  } catch (err) {
    await finish(page, browser, observed, { name: 'STAGE2', failure: err });
  }
})();
