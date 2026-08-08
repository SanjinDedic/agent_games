// Stage 1 — admin claims the deployment, creates a league and two teams.
//
// Everything here is setup for the two stages that carry the actual coverage
// (02 submissions, 03 simulation + progress). It is a stage rather than a
// fixture because the first-run setup form only exists on an unclaimed
// deployment, and driving it through the browser is the only way to prove the
// claim flow still works.
//
//   NODE_PATH="$HOME/.agent-games-playwright/node_modules" \
//     node .claude/skills/tester_skill/manual_tests/01_admin_setup.js
//
// Assumes a fresh stack (docker compose down -v && up) with
// SEED_SAMPLE_DATA=false, which run_playwright_tests.sh guarantees.
const {
  BASE, saveState, launchPage, waitForToast, dismissToasts, finish,
} = require('./_helpers');

const RUN = Math.floor(1000 + Math.random() * 9000);

const ADMIN = { name: `admin${RUN}`, password: 'AdminPass123' };
const LEAGUE = { name: `qa_league_${RUN}`, game: 'greedy_pig' };
const TEAMS = [
  { name: `alpha${RUN}`, password: 'AlphaPass1' },
  { name: `bravo${RUN}`, password: 'BravoPass1' },
];

(async () => {
  const { browser, page, observed } = await launchPage();

  try {
    // 1.1 claim the deployment. /Login serves the setup form while no admin
    // row exists and the login form afterwards, so the button text is what
    // tells the two apart.
    await page.goto(`${BASE}/Login`, { waitUntil: 'domcontentloaded' });
    await page.waitForSelector('button:has-text("Create account")', { timeout: 20000 });
    await page.fill('#admin_name', ADMIN.name);
    await page.fill('#admin_password', ADMIN.password);
    await page.click('button:has-text("Create account")');
    await page.waitForURL('**/Home', { timeout: 20000 });
    console.log(`[1.1] claimed the deployment as "${ADMIN.name}" -> /Home`);

    // 1.2 create the league. The card button and the modal button carry the
    // same label, so the modal one is addressed through the modal.
    await page.click('button:has-text("Create League")');
    const modal = page.locator('div.fixed').filter({
      has: page.locator('h2:text-is("Create New League")'),
    });
    await modal.waitFor({ timeout: 15000 });
    await modal.locator('#leagueName').fill(LEAGUE.name);
    await modal.locator('#gameName').selectOption(LEAGUE.game);
    await modal.locator('button:has-text("Create League")').click();
    await waitForToast(page, 'League created successfully!');
    // The modal stays open showing the join link until dismissed.
    await modal.locator('button:has-text("Done")').click();
    await modal.waitFor({ state: 'detached', timeout: 10000 });
    console.log(`[1.2] created league ${LEAGUE.name} (${LEAGUE.game})`);

    // 1.3 create the teams on the site-wide roster. Teams created here land in
    // the "unassigned" holding pen; 1.4 moves them into the league.
    await dismissToasts(page);
    await page.click('nav a:has-text("Teams")');
    await page.waitForURL('**/Teams', { timeout: 20000 });
    await page.waitForSelector('h1:has-text("Team Management")', { timeout: 15000 });
    for (const team of TEAMS) {
      await page.click('button:has-text("Add a new team")');
      await page.fill('input[placeholder="Enter team name *"]', team.name);
      await page.fill('input[placeholder="Enter team password *"]', team.password);
      await page.fill('input[placeholder="Enter school name (optional)"]', 'Test School');
      await page.click('button:has-text("Add Team")');
      await waitForToast(page, 'Team created successfully');
      await page.waitForSelector(`span:text-is("${team.name}")`, { timeout: 15000 });
      console.log(`[1.3] created team ${team.name}`);
    }

    // 1.4 assign both teams to the league from the home page's unassigned card.
    await dismissToasts(page);
    await page.click('nav a:has-text("Home")');
    await page.waitForURL('**/Home', { timeout: 20000 });
    const unassigned = page.locator('div.bg-white').filter({
      has: page.locator('h2:text-is("Unassigned Teams")'),
    }).first();
    await unassigned.waitFor({ timeout: 15000 });
    for (const team of TEAMS) {
      const row = unassigned.locator('li').filter({ hasText: team.name });
      await row.waitFor({ timeout: 15000 });
      await row.locator('select').selectOption({ label: LEAGUE.name });
      await row.locator('button:has-text("Assign")').click();
      await waitForToast(page, `${team.name} assigned to ${LEAGUE.name}`);
      console.log(`[1.4] assigned ${team.name} to ${LEAGUE.name}`);
    }

    // 1.5 the league card must now count both teams, and opening it gives the
    // league id the later stages address the workspace with.
    const leagueCard = page.locator('div.bg-white').filter({
      has: page.locator(`span:text-is("${LEAGUE.name}")`),
    }).first();
    await leagueCard.locator(`text=${TEAMS.length} teams`).waitFor({ timeout: 20000 });
    await leagueCard.locator(`span:text-is("${LEAGUE.name}")`).click();
    await page.waitForURL('**/Classroom/**', { timeout: 20000 });
    const leagueId = Number(page.url().match(/\/Classroom\/(\d+)/)[1]);
    console.log(`[1.5] league ${LEAGUE.name} has ${TEAMS.length} teams (id ${leagueId})`);

    saveState({ run: RUN, admin: ADMIN, league: { ...LEAGUE, id: leagueId }, teams: TEAMS });
    await finish(page, browser, observed, { name: 'STAGE1' });
  } catch (err) {
    saveState({ run: RUN, admin: ADMIN, league: LEAGUE, teams: TEAMS });
    await finish(page, browser, observed, { name: 'STAGE1', failure: err });
  }
})();
