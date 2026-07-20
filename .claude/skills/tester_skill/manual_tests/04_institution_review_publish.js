// Stage 4 of docs/integration-test-manual.md — Institution (COMPETITION flow
// only: reviews the Stage-3 teams' league; the classroom flow has no
// review/publish stage):
//   4.1 login  4.2 select the league on the Simulation page (record league id)
//   4.3 review team submissions (read-only viewer, prev/next paging)
//   4.4 plagiarism assessment via OpenAI  4.5 run a 100-round simulation
//   4.6 publish the results + verify the public /results/<link> page  4.7 logout
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
    await page.waitForURL('**/InstitutionTeam', { timeout: 20000 });
    console.log('[4.1] institution logged in');

    // 4.2 select the league on the Simulation page
    await page.click('a:has-text("League Simulation"), button:has-text("League Simulation")');
    await page.waitForURL('**/InstitutionLeagueSimulation', { timeout: 15000 });
    await page.click(`h3:has-text("${state.leagueName}")`);
    await page.waitForSelector(`text=Selected League: ${state.leagueName} (greedy_pig)`, { timeout: 15000 });
    console.log('[4.2] league selected on Simulation page');

    // 4.3 review submissions
    await page.click('button:has-text("View League Submissions")');
    await page.waitForURL('**/InstitutionLeagueSubmissions/*', { timeout: 20000 });
    const leagueId = page.url().split('/').pop();
    await page.waitForSelector(`h1:has-text("League Submissions: ${state.leagueName}")`, { timeout: 20000 });
    await page.waitForSelector('span:has-text("League ID:")');
    console.log(`[4.3] submissions page open, league id = ${leagueId}`);

    // Every Stage-3 team must appear with its 2 valid submissions, pageable in the viewer.
    for (const team of state.teams) {
      const card = page.locator(`button:has(div.font-medium:text-is("${team.name}"))`);
      await card.waitFor({ timeout: 15000 });
      const cardText = await card.innerText();
      if (!/2 submissions/.test(cardText)) {
        throw new Error(`team card for ${team.name} does not show 2 submissions: "${cardText.replace(/\n/g, ' | ')}"`);
      }
      await card.click();
      await page.waitForSelector('text=Submission 2 of 2', { timeout: 15000 });
      await page.click('button:has-text("← Prev")');
      await page.waitForSelector('text=Submission 1 of 2', { timeout: 15000 });
      await page.click('button:has-text("Next →")');
      await page.waitForSelector('text=Submission 2 of 2', { timeout: 15000 });
      console.log(`  reviewed ${team.name}: 2 submissions, prev/next paging works`);
    }

    // 4.4 plagiarism assessment on the first team (needs >= 2 submissions)
    const assessTeam = state.teams[0].name;
    await page.click(`button:has(div.font-medium:text-is("${assessTeam}"))`);
    const [assessResp] = await Promise.all([
      page.waitForResponse((r) => r.url().includes('/ai/assess-plagiarism'), { timeout: 180000 }),
      page.click(`button:has-text("Assess ${assessTeam}")`),
    ]);
    const assessBody = await assessResp.json().catch(() => ({}));
    if (!assessResp.ok()) {
      throw new Error(`assess-plagiarism HTTP ${assessResp.status()}: ${JSON.stringify(assessBody).slice(0, 400)}`);
    }
    await page.waitForSelector(`h3:has-text("Assessment: ${assessTeam}")`, { timeout: 15000 });
    await page.waitForSelector('h4:has-text("Deterministic Analysis")');
    await page.waitForSelector('h4:has-text("AI Analysis")');
    const verdict = assessBody.verdict || {};
    console.log(`[4.4] plagiarism report shown for ${assessTeam}:`);
    console.log(`      deterministic: ${assessBody.deterministic_concern_level}`);
    console.log(`      progression=${verdict.progression_verdict} ai_generated=${verdict.ai_generation_verdict} overall=${verdict.overall_concern_level}`);
    await page.click('div.fixed button:has-text("Close")');

    // 4.5 run the simulation (100 rounds)
    await page.goBack();
    await page.waitForURL('**/InstitutionLeagueSimulation', { timeout: 15000 });
    await page.waitForSelector(`text=Selected League: ${state.leagueName} (greedy_pig)`, { timeout: 15000 });
    await page.fill('input[type="number"]', '100');

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
    await page.waitForSelector('select', { timeout: 30000 });
    // Ranking table should list the Stage-3 teams
    for (const team of state.teams) {
      await page.waitForSelector(`text=${team.name}`, { timeout: 15000 });
    }
    console.log('[4.5] simulation ran; results table shows all teams');

    // 4.6 publish + verify the public results page
    const [pubResp] = await Promise.all([
      page.waitForResponse((r) => r.url().includes('/institution/publish-results'), { timeout: 60000 }),
      page.click('button:has-text("PUBLISH RESULT")'),
    ]);
    const pubBody = await pubResp.json().catch(() => ({}));
    if (!pubResp.ok() || !pubBody.publish_link) {
      throw new Error(`publish-results HTTP ${pubResp.status()}: ${JSON.stringify(pubBody).slice(0, 400)}`);
    }
    await page.waitForSelector('text=Results published successfully!', { timeout: 15000 });
    const publishedUrl = `${BASE}/results/${pubBody.publish_link}`;
    console.log(`[4.6] published: ${publishedUrl}`);

    // The manual expects the published run to be tagged "(Published)" in the dropdown
    // and listed under "Published Results" without a reload — record what happens.
    const taggedNow = (await page.locator('select option:has-text("(Published)")').count()) > 0;
    const listedNow = (await page.locator('h3:has-text("Published Results")').count()) > 0;
    observed.notes = observed.notes || [];
    observed.notes.push(`after publish (no reload): dropdown "(Published)" tag=${taggedNow}, Published Results section=${listedNow}`);
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.click(`h3:has-text("${state.leagueName}")`);
    await page.waitForSelector('select', { timeout: 20000 });
    const taggedAfterReload = (await page.locator('select option:has-text("(Published)")').count()) > 0;
    const listedAfterReload = (await page.locator('h3:has-text("Published Results")').count()) > 0;
    observed.notes.push(`after reload: dropdown "(Published)" tag=${taggedAfterReload}, Published Results section=${listedAfterReload}`);

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
