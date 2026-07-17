// Stage 1 of docs/integration-test-manual.md — Admin:
//   1.1 login  1.2 create two institutions  1.3 delete one
//   1.4 backup + restore round-trip  1.5 configure OpenAI key  1.6 logout
//
// Requires OPENAI_API_KEY in the environment (a real, funded sk-... key).
// Records the kept institution's credentials into the state file for Stage 2.
//   NODE_PATH="$HOME/.agent-games-playwright/node_modules" \
//   OPENAI_API_KEY=sk-... node .claude/skills/tester_skill/manual_tests/01_admin_setup.js
//
// Steps run independently where possible: a failing step is recorded (and the
// script exits 1 at the end) but later steps still run, so one broken feature
// doesn't hide the state of the others. Note on 1.4 backup/restore:
// admin_backup._get_s3_client() ignores S3_ENDPOINT_URL, so it always talks to
// real AWS — with the default MinIO creds it 500s (InvalidAccessKeyId); with
// real creds (.aws.env) it works, but the MANUAL dump lands in the production
// backup bucket and the restore replays the newest dump (its own) into the
// local DB.
const {
  BASE, saveState, launchPage, acceptDialogs, waitForToast, finish,
} = require('./_helpers');

const RUN = Math.floor(1000 + Math.random() * 9000);
const KEEP = {
  name: `Test Institution Keep ${RUN}`,
  contact_person: 'QA Tester',
  contact_email: 'qa+keep@example.com',
  password: 'KeepPass123',
};
const DEL = {
  name: `Test Institution Delete ${RUN}`,
  contact_person: 'QA Deleter',
  contact_email: 'qa+delete@example.com',
  password: 'DeletePass123',
};

async function createInstitution(page, inst) {
  await page.click('button:has-text("Add Institution")');
  await page.fill('#name', inst.name);
  await page.fill('#contact_person', inst.contact_person);
  await page.fill('#contact_email', inst.contact_email);
  await page.fill('#password', inst.password);
  // Subscription expiry: leave the default (1 year); Docker access: leave unchecked.
  await page.click('button:has-text("Create Institution")');
  await waitForToast(page, 'Institution created successfully');
  await page.waitForSelector(`tr:has-text("${inst.name}")`, { timeout: 15000 });
  console.log(`  created institution: ${inst.name}`);
}

(async () => {
  if (!process.env.OPENAI_API_KEY) throw new Error('OPENAI_API_KEY env var is required');
  const { browser, page, observed } = await launchPage();
  acceptDialogs(page, observed);

  const results = [];
  // Fatal steps abort the stage (later steps can't work without them);
  // non-fatal failures are recorded and the run continues.
  async function step(name, fatal, fn) {
    try {
      await fn();
      results.push(`${name}: PASS`);
      console.log(`[${name}] PASS`);
    } catch (err) {
      results.push(`${name}: FAIL — ${err.message}`);
      console.error(`[${name}] FAIL — ${err.message}`);
      const shot = `/tmp/agent_games_stage1_${name.replace(/[^\w]/g, '_')}.png`;
      await page.screenshot({ path: shot, fullPage: true }).catch(() => {});
      console.error(`  screenshot: ${shot}`);
      if (fatal) throw err;
    }
  }

  try {
    await step('1.1 admin login', true, async () => {
      await page.goto(`${BASE}/Admin`, { waitUntil: 'domcontentloaded' });
      await page.fill('#admin_name', 'admin');
      await page.fill('#admin_password', 'admin');
      await page.click('button:has-text("Login")');
      await page.waitForURL('**/AdminInstitutions', { timeout: 20000 });
      await page.waitForSelector('h1:has-text("Institution Management")');
    });

    await step('1.2 create two institutions', true, async () => {
      await createInstitution(page, KEEP);
      await createInstitution(page, DEL);
    });

    await step('1.3 delete one institution', false, async () => {
      await page.locator(`tr:has-text("${DEL.name}")`).locator('button[title="Delete Institution"]').click();
      await waitForToast(page, 'deleted successfully');
      await page.waitForSelector(`tr:has-text("${DEL.name}")`, { state: 'detached', timeout: 15000 });
      if (!(await page.locator(`tr:has-text("${KEEP.name}")`).count())) {
        throw new Error('KEPT institution row disappeared after deleting the other one');
      }
    });

    await step('1.4 backup + restore', false, async () => {
      await page.click('a:has-text("Backups"), button:has-text("Backups")');
      await page.waitForURL('**/AdminBackup', { timeout: 15000 });
      await page.waitForSelector('h1:has-text("Database Backups")');
      const [backupResp] = await Promise.all([
        page.waitForResponse((r) => r.url().includes('/admin/backup-database'), { timeout: 120000 }).catch(() => null),
        page.click('button:has-text("Create Backup")'),
      ]);
      // A CORS-stripped 500 never yields a response object — treat both as failure.
      if (!backupResp || !backupResp.ok()) {
        throw new Error(`backup-database failed (HTTP ${backupResp ? backupResp.status() : 'blocked/no response'})`);
      }
      await waitForToast(page, 'Backup created', 60000);
      await page.waitForSelector('table tbody tr', { timeout: 15000 });
      console.log('  backup created');

      const [restoreResp] = await Promise.all([
        page.waitForResponse((r) => r.url().includes('/admin/restore-database'), { timeout: 180000 }).catch(() => null),
        page.locator('table tbody tr').first().locator('button:has-text("Restore")').click(),
      ]);
      if (!restoreResp || !restoreResp.ok()) {
        throw new Error(`restore-database failed (HTTP ${restoreResp ? restoreResp.status() : 'blocked/no response'})`);
      }
      await waitForToast(page, 'Database restored', 60000);
      console.log('  restore completed');
    });

    await step('1.5 configure OpenAI key', true, async () => {
      await page.click('a:has-text("API Keys"), button:has-text("API Keys")');
      await page.waitForURL('**/AdminAPIKeys', { timeout: 15000 });
      await page.waitForSelector('h1:has-text("API Keys Configuration")');
      await page.fill('input[placeholder="sk-..."]', process.env.OPENAI_API_KEY);
      const [valResp] = await Promise.all([
        page.waitForResponse((r) => r.url().includes('/ai/api-keys/validate'), { timeout: 60000 }),
        page.click('button:has-text("Validate")'),
      ]);
      const valBody = await valResp.json().catch(() => ({}));
      if (!valResp.ok() || !valBody.valid) {
        throw new Error(`OpenAI key failed validation: HTTP ${valResp.status()} ${JSON.stringify(valBody)}`);
      }
      await waitForToast(page, 'OpenAI key is valid');
      await page.click('button:has-text("Save Changes")');
      await waitForToast(page, 'API keys updated successfully');
      await page.waitForSelector('span:has-text("Configured")', { timeout: 15000 });
    });

    await step('1.6 logout', false, async () => {
      await page.click('button:has-text("Logout")');
      await page.waitForURL('**/Admin', { timeout: 15000 });
    });

    saveState({ run: RUN, institution: KEEP, deletedInstitution: DEL.name, stage1Results: results });
    const failed = results.filter((r) => r.includes('FAIL'));
    console.log('\n=== Stage 1 summary ===');
    results.forEach((r) => console.log('  ' + r));
    await finish(page, browser, observed, { name: 'STAGE1', failure: failed.length ? new Error(`${failed.length} step(s) failed`) : undefined });
  } catch (err) {
    saveState({ run: RUN, institution: KEEP, deletedInstitution: DEL.name, stage1Results: results });
    console.log('\n=== Stage 1 summary (aborted) ===');
    results.forEach((r) => console.log('  ' + r));
    await finish(page, browser, observed, { name: 'STAGE1', failure: err });
  }
})();
