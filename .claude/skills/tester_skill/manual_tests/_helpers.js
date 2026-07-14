// Shared helpers for the numbered manual-test scripts (01_..., 02_..., ...).
// Run each script with the permanent Playwright install (never installed in the repo):
//   NODE_PATH="$HOME/.agent-games-playwright/node_modules" node .claude/skills/tester_skill/manual_tests/01_admin_setup.js
//
// Values recorded by one stage for the next (signup URL, league id, ...) live in a
// JSON state file: STATE_FILE env var, default /tmp/agent_games_manual_state.json.
const fs = require('fs');
const { chromium } = require('playwright');

const BASE = process.env.BASE_URL || 'http://localhost:3000';
const STATE_FILE = process.env.STATE_FILE || '/tmp/agent_games_manual_state.json';

function loadState() {
  try { return JSON.parse(fs.readFileSync(STATE_FILE, 'utf8')); } catch { return {}; }
}

function saveState(patch) {
  const next = { ...loadState(), ...patch };
  fs.writeFileSync(STATE_FILE, JSON.stringify(next, null, 2));
  return next;
}

// Launch a browser page that records every react-toastify toast, browser console
// error, page error, and native dialog message so the run can be audited afterwards.
async function launchPage() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  const observed = { toasts: [], consoleErrors: [], pageErrors: [], dialogs: [] };

  // Toasts unmount after a few seconds; a MutationObserver catches them all.
  await context.addInitScript(() => {
    window.__toasts = [];
    const seen = new Set();
    const record = () => {
      document.querySelectorAll('.Toastify__toast').forEach((el) => {
        const text = el.textContent.trim();
        const key = text + '|' + (el.getAttribute('id') || '');
        if (text && !seen.has(key)) { seen.add(key); window.__toasts.push(text); }
      });
    };
    // documentElement doesn't exist yet at init-script time; document itself is a valid Node.
    new MutationObserver(record).observe(document, { childList: true, subtree: true });
  });

  page.on('console', (m) => { if (m.type() === 'error') observed.consoleErrors.push(m.text()); });
  page.on('pageerror', (e) => observed.pageErrors.push(String(e)));

  return { browser, context, page, observed };
}

// Auto-accept native confirm()/prompt() dialogs, recording each message.
// promptText is typed into window.prompt dialogs when provided.
function acceptDialogs(page, observed, promptText) {
  page.on('dialog', async (dialog) => {
    observed.dialogs.push(`[${dialog.type()}] ${dialog.message()}`);
    await dialog.accept(promptText);
  });
}

async function collectToasts(page, observed) {
  const toasts = await page.evaluate(() => window.__toasts || []).catch(() => []);
  for (const t of toasts) if (!observed.toasts.includes(t)) observed.toasts.push(t);
  return observed.toasts;
}

// Wait until a toast containing `text` has been shown (checks the full history,
// not just currently-visible toasts).
async function waitForToast(page, text, timeout = 20000) {
  await page.waitForFunction(
    (t) => (window.__toasts || []).some((x) => x.includes(t)),
    text,
    { timeout }
  );
}

// Dismiss any visible toasts (close-on-click) so they stop intercepting clicks.
// Needed because react-toastify pauses its auto-dismiss timer when the window
// is unfocused — permanently, in a headless browser — and the top-center stack
// overlaps the hint panel. Toast texts are already recorded by the observer.
async function dismissToasts(page) {
  await page.evaluate(() => document.querySelectorAll('.Toastify__toast').forEach((t) => t.click()));
  await page.locator('.Toastify__toast').first().waitFor({ state: 'detached', timeout: 5000 }).catch(() => {});
}

// Monaco is React-controlled: setValue via the editor API is the only reliable way
// to change code (DOM typing doesn't fire React's onChange consistently).
async function setMonacoValue(page, code) {
  await page.waitForSelector('.monaco-editor', { timeout: 60000 });
  await page.waitForFunction(() => (window.monaco?.editor?.getEditors?.() ?? []).length > 0, { timeout: 60000 });
  await page.evaluate((c) => window.monaco.editor.getEditors()[0].setValue(c), code);
}

async function getMonacoValue(page) {
  await page.waitForSelector('.monaco-editor', { timeout: 60000 });
  await page.waitForFunction(() => {
    const eds = window.monaco?.editor?.getEditors?.() ?? [];
    return eds.length > 0 && eds[0].getValue().trim().length > 10;
  }, { timeout: 60000 });
  return page.evaluate(() => window.monaco.editor.getEditors()[0].getValue());
}

// Click "Submit Code" and return {status, body} from the submit response.
// Success = HTTP 200 with submission_id; validation failure = HTTP 400 with detail.
// `endpoint` picks the response to assert on: agent submissions (default) or
// tutorial exercises ('/tutorial/submit-exercise').
async function submitCode(page, timeout = 120000, endpoint = '/user/submit-agent') {
  const [resp] = await Promise.all([
    page.waitForResponse((r) => r.url().includes(endpoint) && r.request().method() === 'POST', { timeout }),
    page.click('button:has-text("Submit Code")'),
  ]);
  const body = await resp.json().catch(() => ({}));
  return { status: resp.status(), ok: resp.ok(), body };
}

// Standard end-of-run report: dumps observed toasts/dialogs/errors as JSON so the
// caller can diff them against the manual's expected texts.
async function finish(page, browser, observed, { name, failure } = {}) {
  await collectToasts(page, observed).catch(() => {});
  if (failure) {
    const shot = `/tmp/agent_games_${name}_failure.png`;
    await page.screenshot({ path: shot, fullPage: true }).catch(() => {});
    console.error(`\n${name} FAILED: ${failure.stack || failure}`);
    console.error(`Screenshot: ${shot}`);
    process.exitCode = 1;
  }
  console.log('\n--- observed ---');
  console.log(JSON.stringify(observed, null, 2));
  await browser.close();
  if (!failure) console.log(`\n${name} PASSED`);
}

module.exports = {
  BASE, STATE_FILE, loadState, saveState, launchPage, acceptDialogs,
  collectToasts, waitForToast, dismissToasts, setMonacoValue, getMonacoValue, submitCode, finish,
};
