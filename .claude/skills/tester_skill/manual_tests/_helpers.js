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
  // HEADED=1 opens a visible browser window; SLOWMO=<ms> slows each action for watching.
  const browser = await chromium.launch({
    headless: !process.env.HEADED,
    slowMo: Number(process.env.SLOWMO || 0),
  });
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

// setValue via the editor API is the only reliable way to change code (DOM typing
// doesn't fire Monaco's content-change event consistently). The submission editors
// are uncontrolled — Monaco owns the buffer — so setValue is also what the app
// itself uses, and it still fires the onChange the page listens to.
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

// Read the tutorial overview's progress line ("<passed> of <total> exercises
// completed") and the list position of one exercise. Both numbers are content,
// not behaviour: exercises get authored in and out of a tutorial, so pinning
// them in a script turns every content edit into a false failure. Callers
// assert the passed count they caused and carry `total`/`position` forward.
// The position must be read BEFORE the exercise passes — the badge shows a ✓
// instead of the number once it is completed.
async function readTutorialOverview(page, exerciseTitle, timeout = 15000) {
  const progress = page.locator('text=/^\\d+ of \\d+ exercises completed$/').first();
  await progress.waitFor({ timeout });
  const line = (await progress.innerText()).trim();
  const counts = line.match(/^(\d+) of (\d+) exercises completed$/);
  if (!counts) throw new Error(`unexpected tutorial progress line: "${line}"`);

  const item = page.locator('li').filter({
    has: page.locator(`button:has-text("${exerciseTitle}")`),
  }).first();
  if (!(await item.count())) {
    throw new Error(`tutorial overview has no exercise titled "${exerciseTitle}"`);
  }
  // First span in the card is the status badge: the 1-based position, or ✓.
  const badge = (await item.locator('button > span').first().innerText()).trim();

  return {
    passed: Number(counts[1]),
    total: Number(counts[2]),
    position: /^\d+$/.test(badge) ? Number(badge) : null,
  };
}

// Read the agent-game panel on /TeamHome. The student landing page leads with
// this panel (the tutorials sit under it): three stat tiles — best placement
// with the size of the field, the recent placements, the valid submission
// count — over one line of activity. Placements render as coloured squares,
// so they are read off each square's title ("3rd against the validation
// bots") rather than its colour, and the tiles a team with no ranked
// submissions shows as "—" come back as null/[].
//
// Placement VALUES are content of a random game and must not be asserted:
// where an agent lands against the bots moves between runs. What holds is the
// shape — how many squares, the best being the best of them, the field size.
async function readAgentPanel(page, timeout = 20000) {
  const panel = page.locator('section').filter({
    has: page.locator('h2:text-is("Agent Game")'),
  });
  await panel.waitFor({ timeout });

  // Each tile is the div carrying its own label; the "Stuck on …" nudge box
  // shares the tile background but has no label div, so it can't match.
  const tile = (label) =>
    panel
      .locator('div.bg-ui-lighter')
      .filter({ has: page.locator(`div:text-is("${label}")`) })
      .first();
  const placements = async (label) => {
    const squares = tile(label).locator('span[title*="against the validation bots"]');
    return (await squares.allInnerTexts()).map((t) => Number(t.trim()));
  };

  const best = await placements('Best placement');
  const fieldSize = (await tile('Best placement').innerText()).match(/of (\d+)/);
  const activity = panel
    .locator('p')
    .filter({ hasText: /^(Last submission|No submissions yet)/ })
    .first();

  return {
    best: best.length ? best[0] : null,
    fieldSize: fieldSize ? Number(fieldSize[1]) : null,
    recent: await placements('Recent placements'),
    validSubmissions: Number(
      (await tile('Valid submissions').innerText()).trim().split('\n')[0]
    ),
    activity: (await activity.innerText()).trim(),
    reachedFirst: (await panel.locator('text=REACHED 1ST').count()) > 0,
    // The "Stuck on <game>?" nudge, shown once a team has many valid
    // submissions and still no 1st place (STUCK_AFTER_VALID_SUBMISSIONS).
    nudge: (await panel.locator('p:has-text("Stuck on")').count()) > 0,
  };
}

// Click "Submit Code" and return {status, body} from the submit response.
// Success = HTTP 200 with submission_id; validation failure = HTTP 400 with detail.
// `endpoint` picks the response to assert on: agent submissions (default) or
// tutorial exercises ('/tutorial/submit-exercise' — a substring match, so it
// catches /tutorial/submit-exercise-result, the only exercise persist path).
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
  collectToasts, waitForToast, dismissToasts, setMonacoValue, getMonacoValue,
  readTutorialOverview, readAgentPanel, submitCode, finish,
};
