import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import useClassroomAPI from '../../Shared/hooks/useClassroomAPI';
import { useTerms } from '../../Shared/terminology';
import StatChip from '../../Shared/Common/StatChip';
import MasteryCell, {
  BAND_BARS,
  BAND_CHIPS,
  confidenceWording,
} from '../../Shared/Progress/MasteryCell';
import MasteryInfoModal from '../../Shared/Progress/MasteryInfoModal';
import ConceptDetailModal from './ConceptDetailModal';

// Concept categories are free-text slugs authored in tutorial_data; render
// them as words without hardcoding the vocabulary, so a new category shows up
// correctly the moment someone authors one.
const prettyCategory = (category) => (category || 'other').replace(/-/g, ' ');

// How many student-and-concept alerts to show before "show all". Enough to
// plan a lesson around, short enough that the list stays a list.
const ATTENTION_PREVIEW = 8;

/** The evidence behind one cell, as a sentence. */
const evidenceLine = (cell) =>
  [
    `passed ${cell.exercises_passed} of ${cell.exercises_touched} attempted`,
    `${cell.attempts} attempt${cell.attempts !== 1 ? 's' : ''}`,
    cell.hints_used
      ? `${cell.hints_used} hint${cell.hints_used !== 1 ? 's' : ''}`
      : null,
  ]
    .filter(Boolean)
    .join(' · ');

/**
 * Concept mastery for one classroom: who needs help with what, what the class
 * as a whole hasn't got, and the grid of evidence underneath.
 *
 * The order of the page is the point. A teacher opens this wanting a name and
 * a topic — "sit with Jayden about dictionaries" — so the alerts come first,
 * the class-wide reteach list second, and the full matrix last, as the working
 * that backs them up.
 *
 * Cells are bands, never percentages: counting attempts cannot justify a
 * decimal place. The underlying score exists only to order things and shows up
 * in tooltips labelled as such. Scoring lives in
 * backend/routes/institution/concept_mastery.py and travels with the payload,
 * so the "how is this worked out" modal always matches the arithmetic.
 */
function ConceptsTab({ league }) {
  const T = useTerms();
  const navigate = useNavigate();
  const { getConceptMatrix } = useClassroomAPI();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showBands, setShowBands] = useState(false);
  const [byCurriculum, setByCurriculum] = useState(false);
  const [showAllAttention, setShowAllAttention] = useState(false);
  const [showScoring, setShowScoring] = useState(false);
  // { conceptId, teamId? } while the drill-down modal is open
  const [modalTarget, setModalTarget] = useState(null);

  useEffect(() => {
    let active = true;
    (async () => {
      setLoading(true);
      const result = await getConceptMatrix(league.id);
      if (!active) return;
      if (result.success) {
        setData(result.data);
        setError('');
      } else {
        setError(result.error);
      }
      setLoading(false);
    })();
    return () => {
      active = false;
    };
  }, [getConceptMatrix, league.id]);

  const teams = data?.teams || [];
  const concepts = data?.concepts || [];

  const teamNames = useMemo(
    () => new Map(teams.map((team) => [team.id, team.name])),
    [teams]
  );
  const conceptsById = useMemo(
    () => new Map(concepts.map((concept) => [concept.id, concept])),
    [concepts]
  );

  // Cell lookup plus each student's overall score, in one pass.
  const { cellMap, teamScores } = useMemo(() => {
    const map = new Map();
    const totals = new Map();
    (data?.cells || []).forEach((cell) => {
      map.set(`${cell.team_id}:${cell.concept_id}`, cell);
      const running = totals.get(cell.team_id) || { sum: 0, count: 0 };
      running.sum += cell.mastery;
      running.count += 1;
      totals.set(cell.team_id, running);
    });
    const scores = new Map();
    totals.forEach(({ sum, count }, teamId) =>
      scores.set(teamId, Math.round(sum / count))
    );
    return { cellMap: map, teamScores: scores };
  }, [data]);

  // Students left to right weakest first, so whoever needs help is nearest
  // the concept names rather than off the right edge of a wide class.
  const sortedTeams = useMemo(() => {
    return [...teams].sort((a, b) => {
      const left = teamScores.get(a.id);
      const right = teamScores.get(b.id);
      // Students with no concept data at all sort last: there is nothing to
      // act on for them here, and they'd otherwise read as a crisis.
      if (left == null && right == null) return a.name.localeCompare(b.name);
      if (left == null) return 1;
      if (right == null) return -1;
      return left - right || a.name.localeCompare(b.name);
    });
  }, [teams, teamScores]);

  // Concept rows: weakest class band first by default, curriculum order (and
  // its category grouping) on request.
  const conceptRows = useMemo(() => {
    if (byCurriculum) return concepts;
    return [...concepts].sort((a, b) => {
      if (a.class_mastery == null && b.class_mastery == null) return 0;
      if (a.class_mastery == null) return 1;
      if (b.class_mastery == null) return -1;
      return (
        a.class_mastery - b.class_mastery ||
        b.needs_attention - a.needs_attention
      );
    });
  }, [concepts, byCurriculum]);

  // Contiguous category runs, for the grouping rows in curriculum order.
  const categoryOf = useMemo(() => {
    const firstOfCategory = new Set();
    let previous = null;
    conceptRows.forEach((concept) => {
      if (concept.category !== previous) {
        firstOfCategory.add(concept.id);
        previous = concept.category;
      }
    });
    return firstOfCategory;
  }, [conceptRows]);

  // The student-and-concept alerts, richest first, with their evidence.
  const attention = useMemo(
    () =>
      (data?.attention || [])
        .map((item) => ({
          ...item,
          concept: conceptsById.get(item.concept_id),
          name: teamNames.get(item.team_id),
          cell: cellMap.get(`${item.team_id}:${item.concept_id}`),
        }))
        .filter((item) => item.concept && item.cell),
    [data, conceptsById, teamNames, cellMap]
  );

  // Class-wide: the concepts most students are stuck on, not just the lowest
  // average — one weak student cannot put a concept on the reteach list.
  const reteach = useMemo(
    () =>
      concepts
        .filter((concept) => concept.needs_attention > 0)
        .sort(
          (a, b) =>
            b.needs_attention - a.needs_attention ||
            a.class_mastery - b.class_mastery
        )
        .slice(0, 4),
    [concepts]
  );

  const classScore = useMemo(() => {
    const reached = concepts.filter((c) => c.class_mastery != null);
    if (!reached.length) return { band: null, reached: 0 };
    const score = Math.round(
      reached.reduce((sum, c) => sum + c.class_mastery, 0) / reached.length
    );
    return {
      band: data.scoring.bands.find((band) => score >= band.minimum),
      reached: reached.length,
    };
  }, [concepts, data]);

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-lg p-6 text-ui">
        Loading concept mastery…
      </div>
    );
  }
  if (error) {
    return <div className="bg-white rounded-lg shadow-lg p-6 text-danger">{error}</div>;
  }
  if (concepts.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-lg p-6 text-ui">
        {`None of the exercises in this ${T.league}'s ${T.tutorials} are tagged with concepts yet, so there is nothing to map.`}
      </div>
    );
  }
  if (teams.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-lg p-6 text-ui">
        {`No ${T.teams} in this ${T.league} yet.`}
      </div>
    );
  }

  const bandLabel = (key) =>
    data.scoring.bands.find((band) => band.key === key)?.label || '';

  const visibleAttention = showAllAttention
    ? attention
    : attention.slice(0, ATTENTION_PREVIEW);

  return (
    <div className="space-y-6">
      {/* ---------------------------------------------------------------
          Who needs help. First on the page because it is the only thing
          here a teacher can act on this afternoon.
      --------------------------------------------------------------- */}
      <div className="bg-white rounded-lg shadow-lg p-6">
        <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 mb-1">
          <h2 className="text-xl font-semibold text-ui-dark">Who needs help</h2>
          <button
            onClick={() => setShowScoring(true)}
            className="text-sm text-primary hover:text-primary-hover transition-colors"
          >
            How is this worked out?
          </button>
        </div>

        {attention.length === 0 ? (
          <p className="text-ui">
            {`Nobody is in the bottom two bands on a concept they have reached. `}
            {`Anything blank in the grid below is simply not reached yet.`}
          </p>
        ) : (
          <>
            <p className="text-sm text-ui mb-4">
              {`${attention.length} ${T.team}-and-concept pair${
                attention.length !== 1 ? 's' : ''
              } worth a look, most serious first. "May be" means the reading `}
              {`rests on fewer than ${data.scoring.min_assessments} exercises.`}
            </p>
            {/* Two per row: each card is one short sentence, and stretching it
                across a wide screen strands the band chip miles from the name
                it belongs to. Reading order stays worst-first, left to right. */}
            <div className="grid gap-2 lg:grid-cols-2">
              {visibleAttention.map((item) => (
                <div
                  key={`${item.team_id}:${item.concept_id}`}
                  className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 px-4 py-2 rounded-lg border border-ui-light hover:border-primary/50 transition-colors"
                >
                  <div className="min-w-0">
                    <p className="text-base text-ui-dark">
                      <button
                        onClick={() =>
                          navigate(
                            `/Classroom/${league.id}/student/${item.team_id}`
                          )
                        }
                        className="font-semibold hover:text-primary transition-colors"
                      >
                        {item.name}
                      </button>{' '}
                      {confidenceWording(item.confidence)} struggling with{' '}
                      <button
                        onClick={() =>
                          setModalTarget({
                            conceptId: item.concept_id,
                            teamId: item.team_id,
                          })
                        }
                        className="font-semibold hover:text-primary transition-colors"
                      >
                        {item.concept.name}
                      </button>
                    </p>
                    <p className="text-sm text-ui">
                      {evidenceLine(item.cell)}
                      {item.concept.under_assessed &&
                        ` · only ${item.concept.exercises_total} exercise${
                          item.concept.exercises_total !== 1 ? 's' : ''
                        } cover this concept`}
                    </p>
                  </div>
                  <span
                    className={`shrink-0 px-2 py-0.5 rounded border text-xs font-semibold ${
                      BAND_CHIPS[item.cell.band_key]
                    }`}
                  >
                    {bandLabel(item.cell.band_key)}
                  </span>
                </div>
              ))}
            </div>
            {attention.length > ATTENTION_PREVIEW && (
              <button
                onClick={() => setShowAllAttention(!showAllAttention)}
                className="mt-3 text-sm text-primary hover:text-primary-hover transition-colors"
              >
                {showAllAttention
                  ? 'Show fewer'
                  : `Show all ${attention.length}`}
              </button>
            )}
          </>
        )}
      </div>

      {/* ---------------------------------------------------------------
          What the whole class hasn't got.
      --------------------------------------------------------------- */}
      {reteach.length > 0 && (
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-xl font-semibold text-ui-dark mb-1">
            Concepts to reteach
          </h2>
          <p className="text-sm text-ui mb-4">
            {`Ranked by how many ${T.teams} are in the bottom two bands, not by `}
            {`the average — one struggling ${T.team} is not a class problem. `}
            {`Click one to see who and open its lesson.`}
          </p>
          <div className="flex flex-wrap gap-3">
            {reteach.map((concept) => (
              <button
                key={concept.id}
                onClick={() => setModalTarget({ conceptId: concept.id })}
                className="px-4 py-3 rounded-lg border border-ui-light text-left hover:border-primary hover:bg-ui-lighter/60 transition-colors min-w-[13rem]"
              >
                <div className="text-base font-semibold text-ui-dark">
                  {concept.name}
                </div>
                <div className="text-sm text-ui mt-0.5">
                  <span className="text-danger font-medium">
                    {concept.needs_attention} of {concept.reached}
                  </span>{' '}
                  {`${T.teams} who reached it need help`}
                </div>
                <div className="text-xs text-ui mt-0.5">
                  Class overall: {bandLabel(concept.band_key)}
                  {concept.under_assessed &&
                    ` · lightly assessed (${concept.exercises_total} exercise${
                      concept.exercises_total !== 1 ? 's' : ''
                    })`}
                </div>
                {/* The share of the class needing help — the same figure the
                    card is ranked by. A bar of the class average would run
                    green here and quietly contradict the line above it. */}
                <div className="mt-2 h-1.5 w-full rounded-full bg-ui-lighter overflow-hidden">
                  <div
                    className="h-full rounded-full bg-danger"
                    style={{
                      width: `${Math.round(
                        (concept.needs_attention / concept.reached) * 100
                      )}%`,
                    }}
                  />
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ---------------------------------------------------------------
          Coverage: how much of the course this map can actually see.
      --------------------------------------------------------------- */}
      <div className="flex flex-wrap gap-3">
        <StatChip
          label="Class overall"
          value={classScore.band ? classScore.band.label : '—'}
          tone={
            !classScore.band
              ? 'plain'
              : classScore.band.band >= 3
                ? 'danger'
                : classScore.band.band === 2
                  ? 'warning'
                  : 'success'
          }
          title="The band the class average falls into, averaged over every concept the class has reached"
        />
        <StatChip
          label="Concepts reached"
          value={`${classScore.reached} of ${concepts.length}`}
          title={`Concepts at least one ${T.team} has attempted an exercise for`}
        />
        {data.under_assessed_concepts > 0 && (
          <StatChip
            label="Lightly assessed"
            value={`${data.under_assessed_concepts} concept${
              data.under_assessed_concepts !== 1 ? 's' : ''
            }`}
            tone="warning"
            title={`Concepts practised on fewer than ${data.scoring.min_assessments} exercises — one or two goes is not enough to judge a student on. Tag or write more exercises for these.`}
          />
        )}
        {data.untagged_exercises > 0 && (
          <StatChip
            label="Untagged exercises"
            value={`${data.untagged_exercises} of ${data.exercises_total}`}
            tone="warning"
            title="Exercises carrying no concept tags — their attempts are invisible on this map"
          />
        )}
      </div>

      {/* ---------------------------------------------------------------
          The evidence: concepts down the side, students across the top.
          Concepts are the rows because their names are long and their
          meaning is the thing being read.
      --------------------------------------------------------------- */}
      <div className="bg-white rounded-lg shadow-lg p-6">
        <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 mb-1">
          <h2 className="text-xl font-semibold text-ui-dark">
            Concepts × {T.teams}
          </h2>
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-sm text-ui cursor-pointer">
              <input
                type="checkbox"
                checked={byCurriculum}
                onChange={(e) => setByCurriculum(e.target.checked)}
                className="cursor-pointer"
              />
              Curriculum order
            </label>
            <label className="flex items-center gap-2 text-sm text-ui cursor-pointer">
              <input
                type="checkbox"
                checked={showBands}
                onChange={(e) => setShowBands(e.target.checked)}
                className="cursor-pointer"
              />
              Show band numbers
            </label>
          </div>
        </div>
        <p className="text-sm text-ui mb-4">
          {data.scoring.bands.map((band, index) => (
            <span key={band.key}>
              {index > 0 && ' · '}
              <span
                className={`inline-block w-3 h-3 rounded-sm align-middle ${
                  BAND_BARS[band.key]
                }`}
              />{' '}
              {band.band} {band.label.toLowerCase()}
            </span>
          ))}
          {' · '}
          <span className="font-bold">·</span> not reached.{' '}
          <button
            onClick={() => setShowScoring(true)}
            className="text-primary hover:text-primary-hover transition-colors"
          >
            How is this worked out?
          </button>
        </p>

        <div className="overflow-x-auto">
          <table className="w-auto">
            <thead>
              <tr className="bg-ui-lighter">
                <th className="px-4 py-2 text-left text-sm font-semibold text-ui-dark sticky left-0 bg-ui-lighter z-10">
                  Concept
                </th>
                {sortedTeams.map((team) => (
                  <th key={team.id} className="px-1 py-2 align-bottom w-10">
                    <button
                      onClick={() =>
                        navigate(`/Classroom/${league.id}/student/${team.id}`)
                      }
                      className="text-sm font-semibold text-ui-dark hover:text-primary transition-colors whitespace-nowrap"
                      title={`Open ${team.name}'s submissions and progress`}
                      // Vertical headers keep the student columns narrow
                      // enough that a whole class fits without scrolling.
                      style={{ writingMode: 'vertical-rl', rotate: '180deg' }}
                    >
                      {team.name}
                    </button>
                  </th>
                ))}
                <th className="px-3 py-2 text-right text-sm font-semibold text-ui-dark border-l border-ui-light">
                  Class
                </th>
              </tr>
            </thead>
            <tbody>
              {conceptRows.map((concept) => (
                <React.Fragment key={concept.id}>
                  {/* Category band — only in curriculum order, where the
                      grouping is contiguous and actually means something. */}
                  {byCurriculum && categoryOf.has(concept.id) && (
                    <tr>
                      <td
                        colSpan={sortedTeams.length + 2}
                        className="px-4 pt-3 pb-1 text-xs uppercase tracking-wide text-ui font-semibold sticky left-0 bg-white"
                      >
                        {prettyCategory(concept.category)}
                      </td>
                    </tr>
                  )}
                  <tr className="border-b border-ui-light hover:bg-ui-lighter/50">
                    <td className="px-4 py-1.5 whitespace-nowrap sticky left-0 bg-white z-10">
                      <button
                        onClick={() =>
                          setModalTarget({ conceptId: concept.id })
                        }
                        className="text-base font-medium text-ui-dark hover:text-primary transition-colors"
                        title={concept.description || concept.name}
                      >
                        {concept.name}
                      </button>
                      {concept.under_assessed && (
                        <span
                          className="ml-1.5 text-xs text-notice-orange font-semibold"
                          title={`Only ${concept.exercises_total} exercise${
                            concept.exercises_total !== 1 ? 's' : ''
                          } practise this concept — fewer than the ${
                            data.scoring.min_assessments
                          } this page treats as a confident reading.`}
                        >
                          ⚠ {concept.exercises_total}×
                        </span>
                      )}
                      {!byCurriculum && (
                        <span className="ml-2 text-xs text-ui">
                          {prettyCategory(concept.category)}
                        </span>
                      )}
                    </td>
                    {sortedTeams.map((team) => {
                      const cell = cellMap.get(`${team.id}:${concept.id}`);
                      return (
                        <td key={team.id} className="px-1 py-1.5 text-center">
                          <MasteryCell
                            band={cell?.band}
                            bandKey={cell?.band_key}
                            showValue={showBands}
                            title={
                              cell
                                ? `${team.name} — ${concept.name}\n` +
                                  `Band ${cell.band}: ${bandLabel(cell.band_key)}\n` +
                                  `${evidenceLine(cell)}` +
                                  (cell.avg_attempts_to_pass
                                    ? `\n${cell.avg_attempts_to_pass} tries to pass on average`
                                    : '') +
                                  `\n(score ${cell.mastery}% — used for ordering only)`
                                : `${team.name} has not reached ${concept.name}`
                            }
                            onClick={() =>
                              setModalTarget({
                                conceptId: concept.id,
                                teamId: team.id,
                              })
                            }
                          />
                        </td>
                      );
                    })}
                    <td className="px-3 py-1.5 text-center border-l border-ui-light">
                      <MasteryCell
                        band={concept.band}
                        bandKey={concept.band_key}
                        showValue={showBands}
                        title={
                          concept.band_key
                            ? `${concept.name} — class: ${bandLabel(
                                concept.band_key
                              )}\n${concept.reached} of ${teams.length} ${
                                T.teams
                              } reached it, ${concept.needs_attention} need help`
                            : `No ${T.team} has reached ${concept.name} yet`
                        }
                        onClick={() =>
                          setModalTarget({ conceptId: concept.id })
                        }
                      />
                    </td>
                  </tr>
                </React.Fragment>
              ))}
              {/* Each student overall, across every concept they've reached */}
              <tr className="bg-ui-lighter/60 border-t-2 border-ui-light">
                <td className="px-4 py-2 text-sm font-semibold text-ui-dark sticky left-0 bg-ui-lighter z-10">
                  Overall
                </td>
                {sortedTeams.map((team) => {
                  const score = teamScores.get(team.id);
                  const band =
                    score == null
                      ? null
                      : data.scoring.bands.find((b) => score >= b.minimum);
                  return (
                    <td key={team.id} className="px-1 py-2 text-center">
                      <MasteryCell
                        band={band?.band}
                        bandKey={band?.key}
                        showValue={showBands}
                        title={
                          band
                            ? `${team.name} overall: ${band.label}`
                            : `${team.name} has not reached any concept yet`
                        }
                      />
                    </td>
                  );
                })}
                <td className="border-l border-ui-light" />
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {modalTarget && (
        <ConceptDetailModal
          concept={conceptsById.get(modalTarget.conceptId)}
          teams={teams}
          cells={data.cells}
          bands={data.scoring.bands}
          minAssessments={data.scoring.min_assessments}
          leagueId={league.id}
          focusTeamId={modalTarget.teamId}
          onClose={() => setModalTarget(null)}
        />
      )}
      {showScoring && (
        <MasteryInfoModal
          scoring={data.scoring}
          onClose={() => setShowScoring(false)}
        />
      )}
    </div>
  );
}

export default ConceptsTab;
