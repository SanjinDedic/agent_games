// Smoke test: demo signup -> join greedy_pig_demo -> submit valid starter code -> logout.
// No screenshots on success; on failure dumps /tmp/agent_games_smoke_failure.png.
// Run with the permanent Playwright install (not in the repo):
//   NODE_PATH="$HOME/.agent-games-playwright/node_modules" node .claude/skills/tester_skill/smoke_test.js
const { chromium } = require('playwright');

const BASE = process.env.SMOKE_BASE_URL || 'http://localhost:3000';
const FAILURE_SHOT = '/tmp/agent_games_smoke_failure.png';
// Unique per run so re-runs without a DB wipe don't collide (alphanumeric, <=10 chars)
const TEAM = 'Smoke' + Math.floor(1000 + Math.random() * 9000);

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await (await browser.newContext({ viewport: { width: 1440, height: 900 } })).newPage();

  const consoleErrors = [];
  page.on('console', (msg) => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });

  try {
    // 1. Demo signup
    await page.goto(`${BASE}/Demo`, { waitUntil: 'domcontentloaded' });
    await page.fill('input[placeholder^="Enter a team name"]', TEAM);
    await page.click('button:has-text("Launch Demo Now")');
    await page.waitForURL('**/AgentLeagueSignUp', { timeout: 30000 });
    console.log(`[1/4] Demo team ${TEAM} signed up`);

    // 2. Join a demo league (greedy_pig_demo preferred, else first available)
    const gp = page.locator('input[name="greedy_pig_demo"]');
    await page.locator('input[type="checkbox"]').first().waitFor({ timeout: 30000 });
    const target = (await gp.count()) ? gp : page.locator('input[type="checkbox"]').first();
    const leagueName = await target.getAttribute('name');
    await target.check();
    await page.click('button:has-text("Join League")');
    await page.waitForURL('**/AgentSubmission', { timeout: 30000 });
    console.log(`[2/4] Joined ${leagueName}`);

    // 3. Wait for Monaco + starter code, submit it unchanged (valid submission)
    await page.waitForSelector('.monaco-editor', { timeout: 60000 });
    await page.waitForFunction(() => {
      const eds = window.monaco?.editor?.getEditors?.() ?? [];
      return eds.length > 0 && eds[0].getValue().trim().length > 10;
    }, { timeout: 60000 });
    const [resp] = await Promise.all([
      page.waitForResponse((r) => r.url().includes('/user/submit-agent'), { timeout: 120000 }),
      page.click('button:has-text("Submit Code")'),
    ]);
    // Success = HTTP 200 with a submission_id; failures are HTTP 400 with `detail`.
    const body = await resp.json();
    if (!resp.ok() || body.submission_id == null) {
      throw new Error(`Submission failed (HTTP ${resp.status()}): ${body.detail ?? JSON.stringify(body)}`);
    }
    console.log(`[3/4] Valid submission accepted: submission_id=${body.submission_id}`);

    // 4. Logout
    await page.click('button:has-text("Logout")');
    await page.waitForURL('**/AgentLogin', { timeout: 15000 });
    console.log('[4/4] Logged out');

    if (consoleErrors.length) {
      console.log('Browser console errors (non-fatal):\n' + consoleErrors.join('\n'));
    }
    console.log('\nSMOKE TEST PASSED');
  } catch (err) {
    await page.screenshot({ path: FAILURE_SHOT }).catch(() => {});
    console.error(`\nSMOKE TEST FAILED: ${err.message}`);
    console.error(`Page screenshot: ${FAILURE_SHOT}`);
    if (consoleErrors.length) console.error('Browser console errors:\n' + consoleErrors.join('\n'));
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
})();
