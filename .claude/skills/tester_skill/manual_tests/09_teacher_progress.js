// Script 09 — Teacher progress dashboards (CLASSROOM flow). Not in the manual
// yet. Stages 05/06 create the work; this stage reads it back from the
// teacher's side, where the whole point of the classroom flow lives: the
// per-exercise grid, the concept map beside it, and the per-student page both
// of them drill into.
//   9.1 teacher login, open the classroom workspace from its Home card
//   9.2 Short Course Progress tab (teacher wording — never "Tutorial
//       Progress"): one row per student, Student 1's single pass is the only
//       ✓ in the grid, the Passed summary row agrees with it, and clicking
//       that cell opens the student's code for the exercise
//   9.3 Concepts tab: the Students × Concepts grid (a row per student, then
//       the Class row), the coverage chips, the "How is this worked out?"
//       modal, and the concept detail modal opened both from a column heading
//       and from a student's cell
//   9.4 the student page both grids link to: agent stats agree with the
//       submissions stage 6 made, Concepts card, per-exercise progress
//   9.5 logout -> /Teacher
//
// Content is authored outside this repo, so nothing here pins the vocabulary:
// concept names, exercise titles and counts are read off the page and only
// their relationships are asserted (the Passed row must agree with the cells
// above it, the modal must name the concept whose heading was clicked).
//
// Reads teacher/classroomName/students from the state file (01, 05, 06).
//   NODE_PATH="$HOME/.agent-games-playwright/node_modules" node .claude/skills/tester_skill/manual_tests/09_teacher_progress.js
const { BASE, loadState, launchPage, finish } = require('./_helpers');

(async () => {
  const state = loadState();
  if (!state.teacher) throw new Error('No teacher in state file — run 01_admin_setup.js first');
  if (!state.classroomName) throw new Error('No classroomName in state file — run 05_teacher_classroom.js first');
  if (!state.students?.length) throw new Error('No students in state file — run 06_student_submissions.js first');

  const [student1, student2] = state.students;
  const { browser, page, observed } = await launchPage();

  try {
    // 9.1 teacher login -> classroom workspace
    await page.goto(`${BASE}/Teacher`, { waitUntil: 'domcontentloaded' });
    await page.waitForSelector('h1:has-text("Teacher Login")', { timeout: 15000 });
    await page.fill('#institution_name', state.teacher.name);
    await page.fill('#institution_password', state.teacher.password);
    await page.click('button:has-text("Login")');
    await page.waitForURL('**/InstitutionHome', { timeout: 20000 });
    await page.click(`button[title="Open the ${state.classroomName} workspace"]`);
    await page.waitForURL('**/Classroom/**', { timeout: 15000 });
    // The workspace renders "Loading…" until the leagues fetch returns; the
    // heading is what says the tab strip is mounted and its clicks will land.
    await page.waitForSelector(`h1:has-text("${state.classroomName}")`, { timeout: 20000 });
    const leagueId = page.url().split('/Classroom/')[1].split('/')[0];
    console.log(`[9.1] teacher logged in, classroom workspace open (league id = ${leagueId})`);

    // 9.2 Short Course Progress — the student × exercise grid.
    // Teacher wording: the tab is "Short Course Progress" (T.Tutorial), and
    // "Tutorial Progress" must not appear anywhere in the tab strip.
    if (await page.locator('button:text-is("Tutorial Progress")').count()) {
      throw new Error('classroom workspace shows a "Tutorial Progress" tab — terminology switch regressed');
    }
    await page.click('button:text-is("Short Course Progress")');
    // The tab switches on the URL, but the previous tab's table stays mounted
    // for a beat — so every table here is picked by a row only it has (the
    // roster has no "Passed" summary row), never by position.
    const matrix = page.locator('table').filter({ has: page.locator('td:text-is("Passed")') }).first();
    await matrix.waitFor({ timeout: 20000 });

    // Columns are numbered, with the exercise title in the header's tooltip.
    const exerciseTitles = await matrix.locator('thead th[title]').evaluateAll(
      (ths) => ths.map((th) => th.getAttribute('title'))
    );
    if (exerciseTitles.length === 0) {
      throw new Error('short course grid has no exercise columns — is the short course still attached to the classroom?');
    }

    const gridRow = (name) =>
      matrix.locator('tr').filter({ has: page.locator(`td:text-is("${name}")`) }).first();
    // Passed cells carry a ✓; attempted-but-not-passed cells carry their
    // attempt count; untouched cells are inert dots (spans, not buttons).
    const passedCells = (name) => gridRow(name).locator('button:text-is("✓")');

    for (const name of [student1.name, student2.name]) {
      await gridRow(name).waitFor({ timeout: 15000 });
    }
    const passed1 = await passedCells(student1.name).count();
    const passed2 = await passedCells(student2.name).count();
    if (passed1 !== 1) {
      throw new Error(`${student1.name} shows ${passed1} passed exercises in the grid, expected the 1 from stage 6`);
    }
    if (passed2 !== 0) {
      throw new Error(`${student2.name} shows ${passed2} passed exercises, expected 0 (stage 6 gives them no exercise work)`);
    }

    // The Passed summary row counts the same cells: exactly one column at
    // 1 of 2 students, every other column at 0.
    const summaryRow = matrix.locator('tr').filter({ has: page.locator('td:text-is("Passed")') }).first();
    const summary = (await summaryRow.locator('td').allInnerTexts())
      .slice(1)
      .map((t) => t.trim());
    const withAPass = summary.filter((t) => t === `1/${state.students.length}`);
    const withNone = summary.filter((t) => t === `0/${state.students.length}`);
    if (withAPass.length !== 1 || withAPass.length + withNone.length !== summary.length) {
      throw new Error(`Passed row reads ${JSON.stringify(summary)}, expected exactly one 1/${state.students.length} column`);
    }
    console.log(`[9.2] grid: ${exerciseTitles.length} exercises × ${state.students.length} students, ` +
      `${student1.name} has the only ✓ and the Passed row agrees`);

    // The cell opens that student's code for that exercise. Which exercise it
    // is comes off the cell's own tooltip, so no title is pinned here.
    const cellTitle = await passedCells(student1.name).first().getAttribute('title');
    const exerciseTitle = cellTitle.split(':')[0].split('—')[1].trim();
    if (!exerciseTitles.includes(exerciseTitle)) {
      throw new Error(`cell names "${exerciseTitle}", which is not one of the grid's exercises`);
    }
    await passedCells(student1.name).first().click();
    const codeModal = page.locator(`div.fixed:has(h3:text-is("${student1.name} — ${exerciseTitle}"))`);
    await codeModal.waitFor({ timeout: 20000 });
    await codeModal.locator('text=Loading submissions…').waitFor({ state: 'detached', timeout: 20000 }).catch(() => {});
    // Stage 6 submitted the starter (all tests failing) and then the fix, so
    // the history holds both outcomes; the passing run is the one that made
    // the ✓ upstairs.
    await codeModal.locator('text=Passed').first().waitFor({ timeout: 15000 });
    await codeModal.locator('button[aria-label="Close"]').click();
    await codeModal.waitFor({ state: 'detached', timeout: 10000 });
    console.log(`[9.2] cell opens ${student1.name}'s code for "${exerciseTitle}" (a passing run is in the history)`);

    // 9.3 Concepts — the mastery map over the same work
    await page.click('button:text-is("Concepts")');
    await page.waitForSelector('h2:has-text("Students × Concepts")', { timeout: 20000 });
    if (await page.locator('h2:has-text("Teams × Concepts")').count()) {
      throw new Error('concepts grid shows team wording on a teacher account — terminology switch regressed');
    }
    // Same rule as above: the concepts grid is the table with the Class row.
    const conceptTable = page.locator('table').filter({ has: page.locator('td:text-is("Class")') }).first();
    await conceptTable.waitFor({ timeout: 20000 });
    // Second header row: the student column, one heading per concept, Overall.
    const conceptHeadings = conceptTable.locator('thead tr').nth(1).locator('th button');
    const conceptCount = await conceptHeadings.count();
    if (conceptCount === 0) {
      throw new Error('concepts grid has no concept columns — are the exercises tagged with concepts?');
    }

    // Coverage chips: "Concepts reached" counts against the same column set.
    const reachedChip = page.locator('div:has(> div:text-is("Concepts reached"))').first();
    const reached = (await reachedChip.innerText()).match(/(\d+) of (\d+)/);
    if (!reached) {
      throw new Error(`"Concepts reached" chip reads "${await reachedChip.innerText()}", expected "<n> of <n>"`);
    }
    if (Number(reached[2]) !== conceptCount) {
      throw new Error(`chip counts ${reached[2]} concepts but the grid has ${conceptCount} columns`);
    }

    // One row per student, plus the Class row averaging them.
    for (const name of [student1.name, student2.name]) {
      await conceptTable.locator(`tr:has(button:text-is("${name}"))`).first().waitFor({ timeout: 15000 });
    }
    await conceptTable.locator('tr:has(td:text-is("Class"))').first().waitFor({ timeout: 15000 });
    console.log(`[9.3] concepts grid: ${conceptCount} concepts × ${state.students.length} students + Class row, ` +
      `${reached[1]} of ${reached[2]} concepts reached`);

    // The scoring explainer must be reachable from the page it explains.
    await page.click('button:has-text("How is this worked out?")');
    const scoringModal = page.locator('div.fixed:has(h3:text-is("How this is worked out"))');
    await scoringModal.waitFor({ timeout: 15000 });
    await scoringModal.locator('button[aria-label="Close"]').click();
    await scoringModal.waitFor({ state: 'detached', timeout: 10000 });

    // A column heading opens that concept. The heading is the authored
    // shortname; the modal titles itself with the full name, which is the
    // first line of the heading's tooltip.
    const firstHeading = conceptHeadings.first();
    const conceptName = (await firstHeading.getAttribute('title')).split('\n')[0].split(' — ')[0];
    await firstHeading.click();
    const conceptModal = page.locator(`div.fixed:has(h3:text-is("${conceptName}"))`);
    await conceptModal.waitFor({ timeout: 15000 });
    await conceptModal.locator('h4:has-text("Exercises teaching this concept")').waitFor({ timeout: 15000 });
    await conceptModal.locator('text=The class').waitFor({ timeout: 15000 });
    await conceptModal.locator('button[aria-label="Close"]').click();
    await conceptModal.waitFor({ state: 'detached', timeout: 10000 });
    console.log(`[9.3] column heading opens the "${conceptName}" concept (exercises listed, class reading shown)`);

    // A student's cell opens the same modal focused on them: the evidence
    // line is the count of exercises they attempted and finished.
    const studentCell = conceptTable
      .locator(`tr:has(button:text-is("${student1.name}"))`)
      .first()
      .locator(`button[title^="${student1.name} — "]`)
      .first();
    if (await studentCell.count()) {
      const cellConcept = (await studentCell.getAttribute('title')).split('\n')[0].split(' — ')[1];
      await studentCell.click();
      const studentModal = page.locator(`div.fixed:has(h3:text-is("${cellConcept}"))`);
      await studentModal.waitFor({ timeout: 15000 });
      await studentModal.locator(`button:has-text("${student1.name}")`).waitFor({ timeout: 15000 });
      await studentModal.locator('text=/attempted \\d+\\/\\d+ · completed \\d+\\/\\d+/').waitFor({ timeout: 15000 });
      await studentModal.locator('button[aria-label="Close"]').click();
      await studentModal.waitFor({ state: 'detached', timeout: 10000 });
      console.log(`[9.3] ${student1.name}'s cell opens "${cellConcept}" with their evidence line`);
    } else {
      // One passed exercise is not always enough to score a band; the dot is
      // a legitimate reading, not a failure.
      console.log(`[9.3] ${student1.name} has no banded concept cell yet (one passed exercise) — drill-down skipped`);
    }

    // Both action lists render (their copy differs when there is nothing to
    // act on, which is the expected state after one passed exercise).
    await page.waitForSelector('h2:has-text("Concepts to focus on")', { timeout: 15000 });
    await page.waitForSelector('h2:has-text("Individual attention")', { timeout: 15000 });

    // 9.4 the student page behind the grid
    await conceptTable.locator(`button:text-is("${student1.name}")`).first().click();
    await page.waitForURL('**/student/**', { timeout: 15000 });
    await page.waitForSelector(`h1:has-text("${student1.name}")`, { timeout: 20000 });
    const stat = async (label) => {
      const spans = await page
        .locator(`div:has(> span:text-is("${label}"))`)
        .first()
        .locator('span')
        .allInnerTexts();
      return (spans[1] || '').trim();
    };
    const validated = Number(await stat('Validated'));
    const attempts = Number(await stat('Agent attempts'));
    // Stage 6 made 2 valid submissions and 1 that never got past the AST
    // gate. The failed one is metadata-only, so the teacher's view is the
    // only place it shows up: attempts must run exactly one ahead of
    // validated. (Not pinned to 3/2 — the same classroom is often used for
    // more agent submissions while developing against a live stack.)
    if (validated < 2 || attempts !== validated + 1) {
      throw new Error(`student page shows ${attempts} attempts / ${validated} validated, ` +
        `expected the 1 rejected submission to be the only difference`);
    }
    await page.waitForSelector('h2:has-text("Agent Submissions")', { timeout: 15000 });
    await page.waitForSelector('h2:has-text("Concepts")', { timeout: 20000 });
    // Terminology again: the student page calls it a Short Course too.
    await page.waitForSelector('h2:has-text("Short Course Progress")', { timeout: 15000 });
    const exerciseChips = page.locator(`div.border.border-ui-light:has(span:text-is("${exerciseTitle}"))`);
    await exerciseChips.first().waitFor({ timeout: 15000 });
    console.log(`[9.4] ${student1.name}'s page: ${attempts} attempts / ${validated} validated, ` +
      `concepts card and per-exercise progress present`);

    await page.click(`a:has-text("Back to ${state.classroomName}")`);
    await page.waitForURL('**/students', { timeout: 15000 });

    // 9.5 logout — teacher accounts return to the teacher login
    await page.click('button:has-text("Logout")');
    await page.waitForURL('**/Teacher', { timeout: 15000 });
    console.log('[9.5] logged out -> /Teacher');

    await finish(page, browser, observed, { name: 'STAGE9' });
  } catch (err) {
    await finish(page, browser, observed, { name: 'STAGE9', failure: err });
  }
})();
