import React, { useEffect, useMemo, useState } from 'react';

import useClassroomAPI from '../../Shared/hooks/useClassroomAPI';
import {
  BAND_CHIPS,
  confidenceWording,
  isAttentionBand,
} from '../../Shared/Progress/MasteryCell';
import MasteryInfoModal from '../../Shared/Progress/MasteryInfoModal';

/**
 * One student's concept profile — the "what is actually wrong here" panel on
 * the student drill-down.
 *
 * Leads with the sentences a teacher can act on ("Ava may be struggling with
 * dictionaries"), then the rest of their concepts as bands. Reads the
 * classroom's concept matrix and keeps this student's row rather than adding a
 * per-student endpoint: the payload is small, and one source for the numbers
 * means the tab and this card can never disagree. Renders nothing at all when
 * the classroom has no concept data, so an untagged course doesn't grow an
 * empty card.
 */
function StudentConceptCard({ leagueId, teamId }) {
  const { getConceptMatrix } = useClassroomAPI();
  const [data, setData] = useState(null);
  const [showScoring, setShowScoring] = useState(false);

  useEffect(() => {
    let active = true;
    (async () => {
      const result = await getConceptMatrix(leagueId);
      if (!active) return;
      if (result.success) setData(result.data);
    })();
    return () => {
      active = false;
    };
  }, [getConceptMatrix, leagueId]);

  const rows = useMemo(() => {
    if (!data) return [];
    const concepts = new Map(data.concepts.map((c) => [c.id, c]));
    return data.cells
      .filter((cell) => String(cell.team_id) === String(teamId))
      .map((cell) => ({ ...cell, concept: concepts.get(cell.concept_id) }))
      .filter((row) => row.concept)
      .sort((a, b) => b.band - a.band || a.mastery - b.mastery);
  }, [data, teamId]);

  if (!data || data.concepts.length === 0) return null;

  const bandLabel = (key) =>
    data.scoring.bands.find((band) => band.key === key)?.label || '';
  const needHelp = rows.filter((row) => isAttentionBand(row.band));
  const doingWell = rows.filter((row) => !isAttentionBand(row.band));

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 mb-4">
        <h2 className="text-xl font-semibold text-ui-dark">Concepts</h2>
        <button
          onClick={() => setShowScoring(true)}
          className="text-sm text-primary hover:text-primary-hover transition-colors"
        >
          How is this worked out?
        </button>
      </div>

      {rows.length === 0 ? (
        <p className="text-ui">No concept-tagged exercises attempted yet.</p>
      ) : (
        <>
          {needHelp.length > 0 ? (
            <div className="space-y-2 mb-5">
              {needHelp.map((row) => (
                <div
                  key={row.concept_id}
                  className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 px-4 py-2 rounded-lg border border-ui-light"
                >
                  <div>
                    <p className="text-base text-ui-dark">
                      {confidenceWording(row.confidence) === 'is'
                        ? 'Struggling with'
                        : 'May be struggling with'}{' '}
                      <span className="font-semibold">{row.concept.name}</span>
                    </p>
                    <p className="text-sm text-ui">
                      {`passed ${row.exercises_passed} of ${row.exercises_touched} attempted · ${row.attempts} attempt${
                        row.attempts !== 1 ? 's' : ''
                      }`}
                      {row.hints_used > 0 &&
                        ` · ${row.hints_used} hint${
                          row.hints_used !== 1 ? 's' : ''
                        }`}
                      {row.concept.under_assessed &&
                        ` · only ${row.concept.exercises_total} exercise${
                          row.concept.exercises_total !== 1 ? 's' : ''
                        } cover this`}
                    </p>
                  </div>
                  <span
                    className={`shrink-0 px-2 py-0.5 rounded border text-xs font-semibold ${
                      BAND_CHIPS[row.band_key]
                    }`}
                  >
                    {bandLabel(row.band_key)}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-ui mb-5">
              Nothing they have reached is in the bottom two bands.
            </p>
          )}

          {doingWell.length > 0 && (
            <>
              <p className="text-sm text-ui mb-2">
                Everything else they have reached, weakest first:
              </p>
              <div className="flex flex-wrap gap-2">
                {doingWell.map((row) => (
                  <div
                    key={row.concept_id}
                    className={`px-3 py-1.5 rounded-lg border ${
                      BAND_CHIPS[row.band_key]
                    }`}
                    title={
                      `${row.concept.name} — ${bandLabel(row.band_key)}\n` +
                      `passed ${row.exercises_passed} of ${row.exercises_touched} attempted exercises` +
                      (row.avg_attempts_to_pass
                        ? ` · ${row.avg_attempts_to_pass} tries to pass on average`
                        : '') +
                      (row.hints_used
                        ? ` · ${row.hints_used} hint${
                            row.hints_used !== 1 ? 's' : ''
                          } revealed`
                        : '')
                    }
                  >
                    <span className="text-sm font-medium">
                      {row.concept.name}
                    </span>
                  </div>
                ))}
              </div>
            </>
          )}
        </>
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

export default StudentConceptCard;
