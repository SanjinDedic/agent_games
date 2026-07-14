// Stage 2 of docs/integration-test-manual.md — Institution:
//   2.1 login as the KEPT institution (from Stage 1 state)
//   2.2 create a greedy_pig league, capture + copy the signup URL
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
    // 2.1 institution login
    await page.goto(`${BASE}/Institution`, { waitUntil: 'domcontentloaded' });
    await page.fill('#institution_name', state.institution.name);
    await page.fill('#institution_password', state.institution.password);
    await page.click('button:has-text("Login")');
    await page.waitForURL('**/InstitutionTeam', { timeout: 20000 });
    console.log('[2.1] institution logged in -> /InstitutionTeam');

    // 2.2 create the league (expiry left blank = 24h default; school league unchecked)
    await page.click('a:has-text("League Management"), button:has-text("League Management")');
    await page.waitForURL('**/InstitutionLeague', { timeout: 15000 });
    await page.fill('#leagueName', leagueName);
    await page.selectOption('#gameName', 'greedy_pig');
    const [createResp] = await Promise.all([
      page.waitForResponse((r) => r.url().includes('/institution/league-create'), { timeout: 30000 }),
      page.click('button:has-text("Create League")'),
    ]);
    const createBody = await createResp.json().catch(() => ({}));
    if (!createResp.ok()) throw new Error(`league-create HTTP ${createResp.status()}: ${JSON.stringify(createBody)}`);
    await waitForToast(page, 'League created successfully!');
    await page.waitForSelector('h4:has-text("League Created Successfully")', { timeout: 15000 });

    const signupUrl = await page
      .locator('h4:has-text("League Created Successfully") ~ div input[readonly], h4:has-text("League Created Successfully") >> xpath=../descendant::input[@readonly]')
      .first()
      .inputValue();
    if (!/\/TeamSignup\/.+/.test(signupUrl)) throw new Error(`Signup URL looks wrong: "${signupUrl}"`);
    console.log(`[2.2] league created: ${leagueName}`);
    console.log(`      signup URL: ${signupUrl}`);

    // copy-icon click should toast (manual step 2.2.5)
    await page.locator('button[title="Copy to clipboard"]').last().click();
    await waitForToast(page, 'Signup URL copied to clipboard!');
    const clipboard = await page.evaluate(() => navigator.clipboard.readText()).catch(() => null);
    if (clipboard !== signupUrl) console.warn(`  NOTE: clipboard content mismatch: ${clipboard}`);

    saveState({
      leagueName,
      signupUrl,
      signupToken: signupUrl.split('/TeamSignup/')[1],
      leagueCreateResponse: createBody,
    });

    // Logout to leave a clean session for Stage 3 (manual says either is fine).
    await page.click('button:has-text("Logout")');
    await page.waitForURL('**/Institution', { timeout: 15000 });
    console.log('[2.x] logged out -> /Institution');

    await finish(page, browser, observed, { name: 'STAGE2' });
  } catch (err) {
    await finish(page, browser, observed, { name: 'STAGE2', failure: err });
  }
})();
