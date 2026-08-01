// Script 10 — Teacher team management (CLASSROOM flow). Covers the surfaces the
// earlier stages don't: the /InstitutionTeam directory page (rebuilt as a real
// table), the Home page's Unassigned Students card, the Students tab's
// add/delete actions, and the StudentDetail plagiarism button's wiring:
//   10.1 teacher login -> /InstitutionHome; the navbar directory link reads
//        "Students" (teacher wording) -> /InstitutionTeam; "Student Management"
//        heading over a Name/School/Classroom/Actions table; each stage-06
//        student's classroom select resolves to the stage-05 classroom
//   10.2 create two students from the directory page (create WITHOUT assign):
//        POST /institution/team-create per student, "Student created
//        successfully" toast, both rows appear with the select on unassigned
//   10.3 assign the first from its row: select the classroom, Assign ->
//        POST /institution/assign-team-to-league, contextual toast, the row's
//        select now resolves to the classroom
//   10.4 Reset on that row opens the shared reset-link modal with the same
//        wording contract stage 08 pins on the Students tab (one shared
//        component serves both callers); Copy toasts
//   10.5 back on /InstitutionHome the Unassigned Students card lists only the
//        second new student, classroom preselected; Assign -> toast, row leaves
//        the card
//   10.6 the classroom workspace Students tab: "Add student" creates AND
//        assigns in one step (both team-create and assign-team-to-league must
//        fire — the create-then-assign semantics guard), toast `Student "X"
//        added to <classroom>`; then delete all three test students via X —
//        the confirm must warn "All their submissions are deleted with them."
//        — leaving exactly the stage-06 roster (state stays clean for re-runs)
//   10.7 StudentDetail: the Assess plagiarism button shows the consent confirm
//        naming OpenAI; DISMISSING it must issue no /ai/assess-plagiarism
//        request (zero OpenAI cost)
//
// Reads teacher (01), classroomName (05) and students (06) from the state
// file; creates only its own TM*-prefixed students and deletes them again.
//   NODE_PATH="$HOME/.agent-games-playwright/node_modules" node .claude/skills/tester_skill/manual_tests/10_team_management.js
const {
  BASE, loadState, launchPage, waitForToast, dismissToasts, finish,
} = require('./_helpers');

(async () => {
  const state = loadState();
  if (!state.teacher) throw new Error('No teacher in state file — run 01_admin_setup.js first');
  if (!state.classroomName) throw new Error('No classroomName in state file — run 05_teacher_classroom.js first');
  if (!state.students?.length) throw new Error('No students in state file — run 06_student_submissions.js first');

  const run = Date.now().toString(36).slice(-5);
  const tmA = `TMa-${run}`;
  const tmB = `TMb-${run}`;
  const tmC = `TMc-${run}`;
  const password = `tmpass${run}`;

  const { browser, context, page, observed } = await launchPage();
  await context.grantPermissions(['clipboard-read', 'clipboard-write'], { origin: BASE });

  // Switchable dialog handler: 10.6 accepts the delete confirms, 10.7 dismisses
  // the plagiarism consent. Registered once — a second page.on would double-handle.
  let dialogMode = 'accept';
  page.on('dialog', async (dialog) => {
    observed.dialogs.push(`[${dialog.type()}] ${dialog.message()}`);
    if (dialogMode === 'accept') await dialog.accept();
    else await dialog.dismiss();
  });

  const rowFor = (name) => page.locator(`tr:has(td:text-is("${name}"))`);
  const selectedLabel = (name) =>
    rowFor(name).locator('select').evaluate((s) => s.selectedOptions[0]?.textContent.trim());
  const waitForPost = (path, action, timeout = 20000) =>
    Promise.all([
      page.waitForResponse((r) => r.url().includes(path) && r.request().method() === 'POST', { timeout }),
      action(),
    ]).then(([resp]) => resp);

  try {
    // 10.1 teacher login, then the navbar directory link
    await page.goto(`${BASE}/Teacher`, { waitUntil: 'domcontentloaded' });
    await page.fill('#institution_name', state.teacher.name);
    await page.fill('#institution_password', state.teacher.password);
    await page.click('button:has-text("Login")');
    await page.waitForURL('**/InstitutionHome', { timeout: 20000 });

    const dirLink = page.locator('a[href="/InstitutionTeam"]');
    await dirLink.waitFor({ timeout: 15000 });
    const dirLabel = (await dirLink.innerText()).trim();
    if (dirLabel !== 'Students') {
      throw new Error(`navbar directory link reads "${dirLabel}", expected teacher wording "Students"`);
    }
    await dirLink.click();
    await page.waitForURL('**/InstitutionTeam', { timeout: 15000 });
    await page.waitForSelector('h1:has-text("Student Management")', { timeout: 15000 });
    for (const header of ['Name', 'School', 'Classroom', 'Actions']) {
      await page.waitForSelector(`th:text-is("${header}")`, { timeout: 15000 });
    }
    for (const s of state.students) {
      await rowFor(s.name).waitFor({ timeout: 15000 });
      const label = await selectedLabel(s.name);
      if (label !== state.classroomName) {
        throw new Error(`${s.name}'s classroom select resolves to "${label}", expected "${state.classroomName}"`);
      }
    }
    console.log(`[10.1] directory table lists ${state.students.length} stage-06 students in ${state.classroomName}`);

    // 10.2 create two unassigned students (the form closes after each create)
    for (const name of [tmA, tmB]) {
      await page.click('button:has-text("Add a new student")');
      await page.fill('input[name="name"]', name);
      await page.fill('input[name="password"]', password);
      const resp = await waitForPost('/institution/team-create', () =>
        page.click('button:text-is("Add Student")')
      );
      if (!resp.ok()) throw new Error(`team-create for ${name}: HTTP ${resp.status()}`);
      await waitForToast(page, 'Student created successfully');
      await rowFor(name).waitFor({ timeout: 15000 });
      const label = await selectedLabel(name);
      if (label !== 'unassigned') {
        throw new Error(`freshly created ${name} resolves to "${label}", expected unassigned`);
      }
    }
    console.log('[10.2] two students created unassigned from the directory page');

    // 10.3 assign the first one from its directory row
    await rowFor(tmA).locator('select').selectOption({ label: state.classroomName });
    const assignResp = await waitForPost('/institution/assign-team-to-league', () =>
      rowFor(tmA).locator('button:has-text("Assign")').click()
    );
    if (!assignResp.ok()) throw new Error(`assign-team-to-league for ${tmA}: HTTP ${assignResp.status()}`);
    await waitForToast(page, `'${tmA}' assigned to ${state.classroomName}`);
    // The page reloads its roster after a successful assign
    await page.waitForFunction(
      ({ name, expected }) => {
        const row = [...document.querySelectorAll('tr')].find((tr) =>
          [...tr.querySelectorAll('td')].some((td) => td.textContent.trim() === name)
        );
        const sel = row?.querySelector('select');
        return sel?.selectedOptions[0]?.textContent.trim() === expected;
      },
      { name: tmA, expected: state.classroomName },
      { timeout: 15000 }
    );
    console.log(`[10.3] ${tmA} assigned to ${state.classroomName} from the directory row`);

    // 10.4 the shared reset-link modal, from its second caller (stage 08 pins
    // the same DOM on the Students tab)
    const resetResp = await waitForPost('/institution/team-password-reset', () =>
      rowFor(tmA).locator('button:has-text("Reset")').click()
    );
    if (!resetResp.ok()) throw new Error(`team-password-reset for ${tmA}: HTTP ${resetResp.status()}`);
    const modal = page.locator('div.fixed:has(h2:has-text("Password reset link"))');
    await modal.locator(`h2:has-text("Password reset link for ${tmA}")`).waitFor({ timeout: 15000 });
    await modal.locator('text=Share this link with the student.').waitFor({ timeout: 15000 });
    await modal.locator('text=The link works once and expires in 48 hours.').waitFor({ timeout: 15000 });
    await modal.locator('button:has-text("Copy")').click();
    await waitForToast(page, 'Password reset link copied to clipboard!');
    await modal.locator('button:has-text("Close")').click();
    await modal.waitFor({ state: 'detached', timeout: 10000 });
    console.log('[10.4] shared reset-link modal works from the directory page');

    // 10.5 the Home unassigned card holds only the second new student
    await page.goto(`${BASE}/InstitutionHome`, { waitUntil: 'domcontentloaded' });
    const card = page.locator('div:has(> div > h2:has-text("Unassigned Students"))').first();
    const tmBRow = card.locator(`li:has(span[title="${tmB}"])`);
    await tmBRow.waitFor({ timeout: 20000 });
    const cardLabel = await tmBRow.locator('select').evaluate((s) => s.selectedOptions[0]?.textContent.trim());
    if (cardLabel !== state.classroomName) {
      throw new Error(`unassigned card preselects "${cardLabel}", expected "${state.classroomName}"`);
    }
    const cardAssign = await waitForPost('/institution/assign-team-to-league', () =>
      tmBRow.locator('button:has-text("Assign")').click()
    );
    if (!cardAssign.ok()) throw new Error(`assign from unassigned card: HTTP ${cardAssign.status()}`);
    await waitForToast(page, `${tmB} assigned to ${state.classroomName}`);
    await tmBRow.waitFor({ state: 'detached', timeout: 15000 });
    console.log(`[10.5] ${tmB} assigned from the Home unassigned card`);

    // 10.6 Students tab: add = create AND assign in one step, then clean up
    const workspaceCard = page.locator(`button[title="Open the ${state.classroomName} workspace"]`);
    await workspaceCard.waitFor({ timeout: 15000 });
    await workspaceCard.click();
    await page.waitForURL('**/Classroom/**', { timeout: 15000 });
    await rowFor(state.students[0].name).waitFor({ timeout: 20000 });

    await page.click('button:has-text("Add student")');
    await page.fill('input[placeholder="Student name *"]', tmC);
    await page.fill('input[placeholder="Password *"]', password);
    const [createResp, assignResp2] = await Promise.all([
      page.waitForResponse((r) => r.url().includes('/institution/team-create') && r.request().method() === 'POST', { timeout: 20000 }),
      page.waitForResponse((r) => r.url().includes('/institution/assign-team-to-league') && r.request().method() === 'POST', { timeout: 20000 }),
      page.click(`button:has-text("Add to ${state.classroomName}")`),
    ]);
    if (!createResp.ok() || !assignResp2.ok()) {
      throw new Error(`Students-tab add: create HTTP ${createResp.status()}, assign HTTP ${assignResp2.status()}`);
    }
    await waitForToast(page, `Student "${tmC}" added to ${state.classroomName}`);
    await rowFor(tmC).waitFor({ timeout: 20000 });
    console.log(`[10.6] ${tmC} created and assigned in one step on the Students tab`);

    await dismissToasts(page);
    for (const name of [tmA, tmB, tmC]) {
      const resp = await waitForPost('/institution/delete-team', () =>
        rowFor(name).locator('button[title="Delete student"]').click()
      );
      if (!resp.ok()) throw new Error(`delete-team for ${name}: HTTP ${resp.status()}`);
      await rowFor(name).waitFor({ state: 'detached', timeout: 15000 });
    }
    const deleteWarnings = observed.dialogs.filter((d) =>
      d.includes('All their submissions are deleted with them.')
    );
    if (deleteWarnings.length !== 3) {
      throw new Error(`expected 3 delete confirms warning about submissions, saw ${deleteWarnings.length}`);
    }
    const rosterCount = await page.locator('tr:has(button[title="Delete student"])').count();
    if (rosterCount !== state.students.length) {
      throw new Error(`roster shows ${rosterCount} students after cleanup, expected ${state.students.length}`);
    }
    console.log('[10.6] all three test students deleted; stage-06 roster intact');

    // 10.7 StudentDetail: consent confirm, dismissed -> no OpenAI call
    let assessRequests = 0;
    page.on('request', (r) => {
      if (r.url().includes('/ai/assess-plagiarism')) assessRequests += 1;
    });
    dialogMode = 'dismiss';
    const student = state.students[0];
    await rowFor(student.name).locator('td').first().click();
    await page.waitForURL('**/student/**', { timeout: 20000 });
    const assessBtn = page.locator('button:has-text("Assess plagiarism")');
    await assessBtn.waitFor({ timeout: 20000 });
    await assessBtn.click();
    await page.waitForTimeout(1500);
    const consent = observed.dialogs.find((d) =>
      d.includes(`This will send ${student.name}'s code submissions to OpenAI for analysis. Continue?`)
    );
    if (!consent) throw new Error('plagiarism consent confirm not shown or wording changed');
    if (assessRequests !== 0) {
      throw new Error(`dismissed consent still issued ${assessRequests} /ai/assess-plagiarism request(s)`);
    }
    dialogMode = 'accept';
    console.log('[10.7] plagiarism consent shown; dismissing it issues no request');

    await page.click('button:has-text("Logout")');
    await page.waitForURL('**/Teacher', { timeout: 15000 });

    await finish(page, browser, observed, { name: 'STAGE10' });
  } catch (err) {
    await finish(page, browser, observed, { name: 'STAGE10', failure: err });
  }
})();
