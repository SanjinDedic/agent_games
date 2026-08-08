// Stage 3 — the admin reads the teams' progress and runs a simulation.
//
// This is the payoff for stages 1 and 2: the submissions stored by the teams
// have to show up on the admin's side (the Submissions grid) and have to be
// what the simulation actually competes (every team present in the run).
//
// Reads the state written by 01_admin_setup.js; needs 02_team_submissions.js to
// have run, or there is nothing to simulate.
//   NODE_PATH="$HOME/.agent-games-playwright/node_modules" \
//     node .claude/skills/tester_skill/manual_tests/03_admin_progress.js
const {
  BASE, loadState, launchPage, waitForToast, dismissToasts, finish,
} = require('./_helpers');

// Each team submitted twice in stage 2 (the rejected attempt stores no code
// row, so it is deliberately not counted here).
const EXPECTED_SUBMISSIONS = 2;

(async () => {
  const state = loadState();
  if (!state.admin || !state.league?.id) {
    throw new Error('No admin/league in the state file — run 01_admin_setup.js first');
  }
  const { admin, league, teams } = state;

  const { browser, page, observed } = await launchPage();

  try {
    // 3.1 log in as the admin. The deployment is claimed by now, so /Login
    // serves the login form rather than the setup form.
    await page.goto(`${BASE}/Login`, { waitUntil: 'domcontentloaded' });
    await page.waitForSelector('button:has-text("Login")', { timeout: 20000 });
    await page.fill('#admin_name', admin.name);
    await page.fill('#admin_password', admin.password);
    await page.click('button:has-text("Login")');
    await page.waitForURL('**/Home', { timeout: 20000 });
    console.log(`[3.1] logged in as ${admin.name}`);

    // 3.2 progress: the submissions grid, one row per team.
    await page.goto(`${BASE}/Classroom/${league.id}/submissions`, {
      waitUntil: 'domcontentloaded',
    });
    await page.waitForSelector('h2:has-text("Agent submissions")', { timeout: 20000 });
    for (const team of teams) {
      const row = page.locator('tbody tr').filter({
        has: page.locator(`td:text-is("${team.name}")`),
      });
      await row.waitFor({ timeout: 20000 });
      // Last-but-one cell is the Total column.
      const total = Number((await row.locator('td').nth(-2).innerText()).trim());
      if (total !== EXPECTED_SUBMISSIONS) {
        throw new Error(
          `${team.name} shows ${total} submissions in the admin grid, expected ${EXPECTED_SUBMISSIONS}`
        );
      }
      // Every stored submission is graded against the validation bots, so each
      // cell carries a placement rather than the "no submission" dot.
      const placements = await row.locator('td button[title*="against the validation bots"]').count();
      if (placements !== EXPECTED_SUBMISSIONS) {
        throw new Error(
          `${team.name} shows ${placements} graded submissions, expected ${EXPECTED_SUBMISSIONS}`
        );
      }
      console.log(`[3.2] ${team.name}: ${total} submissions, all graded`);
    }

    // 3.3 run a simulation over those submissions.
    await page.goto(`${BASE}/Classroom/${league.id}/simulation`, {
      waitUntil: 'domcontentloaded',
    });
    await page.waitForSelector('button:has-text("RUN SIMULATION")', { timeout: 20000 });
    await page.fill('#simulation-game-count', '20');
    const [simResp] = await Promise.all([
      page.waitForResponse(
        (r) => r.url().includes('/admin/run-simulation') && r.request().method() === 'POST',
        { timeout: 300000 }
      ),
      page.click('button:has-text("RUN SIMULATION")'),
    ]);
    const simBody = await simResp.json().catch(() => ({}));
    if (!simResp.ok()) {
      throw new Error(
        `simulation failed: HTTP ${simResp.status()} ${JSON.stringify(simBody).slice(0, 300)}`
      );
    }
    await waitForToast(page, 'Simulation completed successfully');

    // Every team's latest agent must have competed — a team missing here means
    // its submission never reached the simulation.
    const competed = Object.keys(simBody.total_points || {});
    for (const team of teams) {
      if (!competed.includes(team.name)) {
        throw new Error(
          `${team.name} is missing from the run: scored agents were ${JSON.stringify(competed)}`
        );
      }
    }
    console.log(
      `[3.3] simulation ran ${simBody.num_simulations} games over ${competed.length} agents`
    );

    // 3.4 the run has to land in the summary panel, not just in the response.
    await dismissToasts(page);
    // "N runs recorded" rather than exactly 1, so re-running this stage against
    // an already-simulated league still reads correctly.
    await page.waitForSelector('text=/\\d+ runs? recorded/', { timeout: 20000 });
    // The chip is a label div over a value div; match the wrapper by its label.
    const agentsChip = page.locator('div.rounded-lg.border').filter({
      has: page.locator('div:text-is("Agents in run")'),
    }).first();
    await agentsChip.waitFor({ timeout: 15000 });
    const chipText = (await agentsChip.innerText()).replace(/\n/g, ' ');
    if (!chipText.includes(String(competed.length))) {
      throw new Error(
        `run summary reports "${chipText}", expected ${competed.length} agents`
      );
    }
    console.log(`[3.4] run summary shows the recorded run with ${competed.length} agents`);

    await finish(page, browser, observed, { name: 'STAGE3' });
  } catch (err) {
    await finish(page, browser, observed, { name: 'STAGE3', failure: err });
  }
})();
