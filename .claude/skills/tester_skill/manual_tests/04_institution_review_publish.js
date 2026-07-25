// Stage 4 of docs/integration-test-manual.md — Institution (COMPETITION flow
// only: reviews the Stage-3 teams' league; the classroom flow has no
// review/publish stage). Post-revamp, everything lives in the league's
// /Classroom/:id/:tab workspace — the old standalone Simulation and
// Submissions pages are gone:
//   4.1 login -> /InstitutionHome
//   4.2 open the league's workspace from its Home card (record league id)
//   4.3 review team submissions on the Submissions tab: one grid row per team,
//       one cell per submission (coloured by validation placement); a cell
//       opens the code modal on that submission, ALL opens it on the newest
//   4.4 plagiarism assessment via OpenAI (from inside the code modal)
//   4.5 run a 100-round simulation on the Simulation tab
//   4.6 publish the results + verify the public /results/<link> page
//   4.7 logout
//
// The Submissions tab is a grid now, not a team-card list: SubmissionsTab.jsx
// renders a table (one row per team, the last 15 submissions as StatusCell
// buttons titled "<team> — submission N of M · ...") and AgentCodeModal.jsx
// holds the read-only Monaco viewer + the "AI plagiarism assessment" button
// (the old per-team "Assess <team>" button is gone).
//
// The Simulation tab is split into SimulationRunner (the RUN SIMULATION
// controls) + SimulationRunSummary (run picker, headline stats, publish box)
// + RunResultsModal (the leaderboard table, opened by "Show results"). The old
// always-visible ranking table and "Selected League: <name> (<game>)" line are
// gone.
//
// Reads institution/league/teams from the state file (stages 1–3);
// writes leagueId, publishedUrl and the plagiarism verdict back.
//   NODE_PATH="$HOME/.agent-games-playwright/node_modules" node .claude/skills/tester_skill/manual_tests/04_institution_review_publish.js
const {
  BASE, loadState, saveState, launchPage, acceptDialogs, waitForToast, finish,
} = require('./_helpers');

(async () => {
  const state = loadState();
  if (!state.institution || !state.leagueName || !state.teams) {
    throw new Error('state file incomplete — run stages 1–3 first');
  }

  const { browser, page, observed } = await launchPage();
  acceptDialogs(page, observed); // plagiarism confirm is a native window.confirm

  try {
    // 4.1 institution login
    await page.goto(`${BASE}/Institution`, { waitUntil: 'domcontentloaded' });
    await page.fill('#institution_name', state.institution.name);
    await page.fill('#institution_password', state.institution.password);
    await page.click('button:has-text("Login")');
    await page.waitForURL('**/InstitutionHome', { timeout: 20000 });
    console.log('[4.1] institution logged in');

    // 4.2 open the Stage-3 league's workspace from its Home card
    const workspaceCard = page.locator(`button[title="Open the ${state.leagueName} workspace"]`);
    await workspaceCard.waitFor({ timeout: 15000 });
    await workspaceCard.click();
    await page.waitForURL('**/Classroom/**', { timeout: 15000 });
    const leagueId = page.url().split('/Classroom/')[1].split('/')[0];
    await page.waitForSelector(`h1:has-text("${state.leagueName}")`, { timeout: 15000 });
    console.log(`[4.2] classroom workspace open, league id = ${leagueId}`);

    // 4.3 review submissions (Submissions tab). :text-is targets the tab
    // button exactly so it can't match other tabs' text.
    await page.click('button:text-is("Submissions")');
    await page.waitForSelector('h2:has-text("Agent submissions")', { timeout: 20000 });
    // Every Stage-3 team gets a grid row with its 2 valid submissions as cells.
    // The code modal opens on whichever cell was clicked and pages prev/next.
    const codeModal = page.locator('div.fixed:has(h3:has-text("— submissions"))');
    for (const team of state.teams) {
      const row = page.locator('tr').filter({ has: page.locator(`td:text-is("${team.name}")`) });
      await row.waitFor({ timeout: 20000 });
      // Only real submissions get a titled cell button; empty slots are spans.
      const cells = row.locator(`button[title^="${team.name} — submission "]`);
      const cellCount = await cells.count();
      if (cellCount !== 2) {
        throw new Error(`grid row for ${team.name} shows ${cellCount} submission cells, expected 2`);
      }
      // Total column (second-to-last cell, beside the ALL button) must agree with the grid.
      const cellsInRow = await row.locator('td').count();
      const total = (await row.locator('td').nth(cellsInRow - 2).innerText()).trim();
      if (total !== '2') {
        throw new Error(`grid row for ${team.name} totals "${total}" submissions, expected 2`);
      }

      // Clicking the OLDEST cell must open the modal on submission 1, not the newest.
      await cells.first().click();
      await codeModal.waitFor({ timeout: 15000 });
      await codeModal.locator('text=Submission 1 of 2').waitFor({ timeout: 15000 });
      await codeModal.locator('button:has-text("Next →")').click();
      await codeModal.locator('text=Submission 2 of 2').waitFor({ timeout: 15000 });
      await codeModal.locator('button:has-text("← Prev")').click();
      await codeModal.locator('text=Submission 1 of 2').waitFor({ timeout: 15000 });
      await codeModal.locator('button[aria-label="Close"]').click();
      await codeModal.waitFor({ state: 'detached', timeout: 10000 });

      // ALL opens the same history on the NEWEST submission.
      await row.locator('button:text-is("ALL")').click();
      await codeModal.locator('text=Submission 2 of 2').waitFor({ timeout: 15000 });
      await codeModal.locator('button[aria-label="Close"]').click();
      await codeModal.waitFor({ state: 'detached', timeout: 10000 });
      console.log(`  reviewed ${team.name}: 2 submission cells, ALL opens the newest, prev/next paging works`);
    }

    // 4.4 plagiarism assessment on the first team (needs >= 2 submissions).
    // The button lives in the code modal now, and acts on the team being read.
    const assessTeam = state.teams[0].name;
    const assessRow = page.locator('tr').filter({ has: page.locator(`td:text-is("${assessTeam}")`) });
    await assessRow.locator('button:text-is("ALL")').click();
    await codeModal.waitFor({ timeout: 15000 });
    const [assessResp] = await Promise.all([
      page.waitForResponse((r) => r.url().includes('/ai/assess-plagiarism'), { timeout: 180000 }),
      codeModal.locator('button:has-text("AI plagiarism assessment")').click(),
    ]);
    const assessBody = await assessResp.json().catch(() => ({}));
    if (!assessResp.ok()) {
      throw new Error(`assess-plagiarism HTTP ${assessResp.status()}: ${JSON.stringify(assessBody).slice(0, 400)}`);
    }
    const report = page.locator(`div.fixed:has(h3:has-text("Assessment: ${assessTeam}"))`);
    await report.waitFor({ timeout: 15000 });
    await report.locator('h4:has-text("Deterministic Analysis")').waitFor({ timeout: 15000 });
    await report.locator('h4:has-text("AI Analysis")').waitFor({ timeout: 15000 });
    const verdict = assessBody.verdict || {};
    console.log(`[4.4] plagiarism report shown for ${assessTeam}:`);
    console.log(`      deterministic: ${assessBody.deterministic_concern_level}`);
    console.log(`      progression=${verdict.progression_verdict} ai_generated=${verdict.ai_generation_verdict} overall=${verdict.overall_concern_level}`);
    await report.locator('button:text-is("Close")').click();
    await report.waitFor({ state: 'detached', timeout: 10000 });
    await codeModal.locator('button[aria-label="Close"]').click();
    await codeModal.waitFor({ state: 'detached', timeout: 10000 });

    // 4.5 run the simulation (100 rounds) on the Simulation tab. The runner
    // names the target league inline ("<name> · <game> · every team's latest
    // agent competes") instead of the old "Selected League:" line.
    await page.click('button:text-is("Simulation")');
    const runner = page.locator('div.bg-white').filter({ has: page.locator('button:has-text("RUN SIMULATION")') }).first();
    await runner.waitFor({ timeout: 15000 });
    const runnerText = await runner.innerText();
    if (!runnerText.includes(state.leagueName) || !runnerText.includes('greedy_pig')) {
      throw new Error(`simulation runner does not name the league/game: "${runnerText.replace(/\n/g, ' | ').slice(0, 200)}"`);
    }
    await page.fill('#simulation-game-count', '100');

    const runSimulationOnce = async () => {
      const [resp] = await Promise.all([
        page.waitForResponse((r) => r.url().includes('/institution/run-simulation'), { timeout: 300000 }),
        page.click('button:has-text("RUN SIMULATION")'),
      ]);
      return { resp, body: await resp.json().catch(() => ({})) };
    };

    let { resp: simResp, body: simBody } = await runSimulationOnce();
    if (simResp.status() === 403 && /Docker access/.test(simBody.detail || '')) {
      // KNOWN MANUAL/APP MISMATCH: the manual says to create the institution with
      // Docker access unchecked, but run-simulation requires it. Flip the toggle
      // via the admin UI (which also exercises that toggle) and retry.
      observed.notes = observed.notes || [];
      observed.notes.push('run-simulation 403 without Docker access — manual says leave it unchecked; enabled via admin toggle to continue');
      console.log('[4.5] FINDING: run-simulation requires Docker access; enabling it via admin UI and retrying');
      const adminCtx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
      const adminPage = await adminCtx.newPage();
      await adminPage.goto(`${BASE}/Admin`, { waitUntil: 'domcontentloaded' });
      await adminPage.fill('#admin_name', 'admin');
      await adminPage.fill('#admin_password', 'admin');
      await adminPage.click('button:has-text("Login")');
      await adminPage.waitForURL('**/AdminInstitutions', { timeout: 20000 });
      const row = adminPage.locator(`tr:has-text("${state.institution.name}")`);
      await row.waitFor({ timeout: 15000 });
      await row.locator('button.rounded-full').click();
      await row.locator('span:has-text("Enabled")').waitFor({ timeout: 15000 });
      await adminCtx.close();
      ({ resp: simResp, body: simBody } = await runSimulationOnce());
    }
    if (!simResp.ok()) throw new Error(`run-simulation HTTP ${simResp.status()}: ${JSON.stringify(simBody).slice(0, 400)}`);
    // The run summary replaces the old always-visible table: run picker +
    // headline chips. The leaderboard itself is behind "Show results".
    await page.waitForSelector('#simulation-run-picker', { timeout: 30000 });
    await page.waitForSelector('text=Games played', { timeout: 15000 });
    await page.waitForSelector(`text=Agents in run`, { timeout: 15000 });
    const runResults = page.locator('div.fixed:has(h3:text-is("Run results"))');
    await page.click('button:has-text("Show results")');
    await runResults.waitFor({ timeout: 15000 });
    // Leaderboard in the modal must list the Stage-3 teams
    for (const team of state.teams) {
      await runResults.locator(`text=${team.name}`).first().waitFor({ timeout: 15000 });
    }
    await runResults.locator('button[aria-label="Close"]').click();
    await runResults.waitFor({ state: 'detached', timeout: 10000 });
    console.log('[4.5] simulation ran; Show results modal lists all teams');

    // 4.6 publish + verify the public results page
    const [pubResp] = await Promise.all([
      page.waitForResponse((r) => r.url().includes('/institution/publish-results'), { timeout: 60000 }),
      page.click('button:has-text("PUBLISH RESULT")'),
    ]);
    const pubBody = await pubResp.json().catch(() => ({}));
    if (!pubResp.ok() || !pubBody.publish_link) {
      throw new Error(`publish-results HTTP ${pubResp.status()}: ${JSON.stringify(pubBody).slice(0, 400)}`);
    }
    const publishedUrl = `${BASE}/results/${pubBody.publish_link}`;
    // Publishing flips the whole box: the LeaguePublish button is replaced by
    // the "this run is live" panel carrying the public URL. (LeaguePublish's own
    // "Results published successfully!" view is never reached here — the parent
    // re-renders on the Redux publish_link first.)
    await page.locator('p:has-text("This run is live for your teams")').waitFor({ timeout: 15000 });
    const liveLink = page.locator(`a[href="/results/${pubBody.publish_link}"]`).first();
    await liveLink.waitFor({ timeout: 15000 });
    console.log(`[4.6] published: ${publishedUrl}`);

    // Without a reload the run picker must tag the run "· Published" and the
    // "Published links (N)" section must appear (the Redux publish_link update
    // drives both) — assert it here rather than only recording it.
    const assertPublishedMarkers = async (when) => {
      const tagged = (await page.locator('#simulation-run-picker option:has-text("· Published")').count()) > 0;
      const listed = (await page.locator('summary:has-text("Published links (1)")').count()) > 0;
      if (!tagged || !listed) {
        throw new Error(`${when}: run picker "· Published" tag=${tagged}, "Published links (1)" section=${listed}`);
      }
      observed.notes = observed.notes || [];
      observed.notes.push(`${when}: run picker tagged "· Published" and "Published links (1)" section present`);
    };
    await assertPublishedMarkers('after publish (no reload)');
    // Reload lands back on the Simulation tab (URL-driven); the workspace
    // re-selects this league automatically, so no card click is needed.
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForSelector('#simulation-run-picker', { timeout: 20000 });
    await assertPublishedMarkers('after reload');

    // public page renders with no login (fresh context would be stricter; new tab is close enough
    // since the public route never sends the Authorization header)
    const publicPage = await (await browser.newContext()).newPage();
    await publicPage.goto(publishedUrl, { waitUntil: 'domcontentloaded' });
    await publicPage.waitForSelector('h1:has-text("Published Results")', { timeout: 20000 });
    for (const team of state.teams) {
      await publicPage.waitForSelector(`text=${team.name}`, { timeout: 15000 });
    }
    await publicPage.close();
    console.log('[4.6b] public results page renders without login and lists the teams');

    // 4.7 logout
    await page.click('button:has-text("Logout")');
    await page.waitForURL('**/Institution', { timeout: 15000 });
    console.log('[4.7] logged out -> /Institution');

    saveState({
      leagueId,
      publishedUrl,
      plagiarism: {
        team: assessTeam,
        deterministic: assessBody.deterministic_concern_level,
        progression: verdict.progression_verdict,
        ai_generated: verdict.ai_generation_verdict,
        overall: verdict.overall_concern_level,
      },
    });
    await finish(page, browser, observed, { name: 'STAGE4' });
  } catch (err) {
    await finish(page, browser, observed, { name: 'STAGE4', failure: err });
  }
})();
