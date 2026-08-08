// Stage 2 — each team logs in and submits an agent.
//
// The submission path is the one thing every other feature depends on: a run
// with no stored submissions has nothing to simulate and nothing to show as
// progress. Both a valid and a rejected submission are exercised, because the
// rejection is what proves the code actually reached the validator rather than
// being waved through.
//
// Reads the admin/league/team state written by 01_admin_setup.js.
//   NODE_PATH="$HOME/.agent-games-playwright/node_modules" \
//     node .claude/skills/tester_skill/manual_tests/02_team_submissions.js
const {
  BASE, loadState, launchPage, dismissToasts,
  setMonacoValue, getMonacoValue, submitCode, finish,
} = require('./_helpers');

async function runTeam(page, team, league) {
  console.log(`\n=== ${team.name} ===`);

  await page.goto(`${BASE}/AgentLogin`, { waitUntil: 'domcontentloaded' });
  await page.fill('#team_name', team.name);
  await page.fill('#team_password', team.password);
  await page.click('button:has-text("Login")');
  await page.waitForURL('**/TeamHome', { timeout: 20000 });
  await page.waitForSelector(`text=You're competing in ${league.name}`, { timeout: 20000 });
  console.log(`[2.1] logged in, landed in ${league.name}`);

  await page.click('a:has-text("Open Agent Workspace")');
  await page.waitForURL('**/AgentSubmission', { timeout: 20000 });

  // 2.2 the starter code the workspace pre-fills must itself be a valid agent.
  const starter = await getMonacoValue(page);
  const valid = await submitCode(page);
  if (!valid.ok || valid.body.submission_id == null) {
    throw new Error(
      `starter-code submission should pass but got HTTP ${valid.status}: ` +
      `${JSON.stringify(valid.body).slice(0, 300)}`
    );
  }
  console.log(`[2.2] valid submission stored (id=${valid.body.submission_id})`);

  // Feedback for the run renders under the editor — without it a team has no
  // way to tell a stored submission from a swallowed one.
  await page.waitForSelector('text=/Simulation Results|Game Results|Feedback/i', { timeout: 30000 });

  // 2.3 an unsafe import must be refused by the AST check before it ever runs.
  await setMonacoValue(page, 'import os\n' + starter);
  const rejected = await submitCode(page);
  if (rejected.ok) {
    throw new Error('a submission importing os unexpectedly passed validation');
  }
  const detail = rejected.body.detail || '';
  if (!detail.includes('Unauthorized import: os')) {
    throw new Error(`unexpected rejection message: HTTP ${rejected.status} "${detail}"`);
  }
  console.log(`[2.3] unsafe submission rejected: "${detail}"`);

  // Leave the good agent as the team's latest — the simulation in stage 3 runs
  // whatever each team last had accepted.
  await setMonacoValue(page, starter);
  const final = await submitCode(page);
  if (!final.ok) {
    throw new Error(`re-submitting the starter agent failed: HTTP ${final.status}`);
  }
  console.log(`[2.4] latest stored agent is the valid one (id=${final.body.submission_id})`);

  await dismissToasts(page);
  await page.click('button:has-text("Logout")');
  await page.waitForURL('**/AgentLogin', { timeout: 15000 });
}

(async () => {
  const state = loadState();
  if (!state.teams || !state.league) {
    throw new Error('No teams/league in the state file — run 01_admin_setup.js first');
  }

  const { browser, page, observed } = await launchPage();
  try {
    for (const team of state.teams) {
      await runTeam(page, team, state.league);
    }
    await finish(page, browser, observed, { name: 'STAGE2' });
  } catch (err) {
    await finish(page, browser, observed, { name: 'STAGE2', failure: err });
  }
})();
