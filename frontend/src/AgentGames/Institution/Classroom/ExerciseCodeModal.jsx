import React, { useEffect, useState } from 'react';

import useClassroomAPI from '../../Shared/hooks/useClassroomAPI';
import CodeHistoryViewer from '../../Shared/Submission/CodeHistoryViewer';
import ExerciseResults from '../../User/ExerciseResults';

/**
 * Modal showing one student's submission history for one exercise: code in a
 * read-only Monaco viewer plus the per-test results of the shown run.
 */
function ExerciseCodeModal({ teamId, teamName, exerciseId, onClose }) {
  const { getStudentExerciseSubmissions } = useClassroomAPI();

  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [index, setIndex] = useState(0);

  useEffect(() => {
    let active = true;
    (async () => {
      setLoading(true);
      const result = await getStudentExerciseSubmissions(teamId, exerciseId);
      if (!active) return;
      if (result.success) {
        // API returns newest first; the viewer navigates oldest -> newest.
        const submissions = [...result.data.submissions].reverse();
        setPayload({ ...result.data, submissions });
        setIndex(submissions.length > 0 ? submissions.length - 1 : 0);
        setError('');
      } else {
        setError(result.error);
      }
      setLoading(false);
    })();
    return () => {
      active = false;
    };
  }, [getStudentExerciseSubmissions, teamId, exerciseId]);

  const submissions = payload?.submissions || [];
  const current = submissions[index];

  return (
    <div
      className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-6"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto p-6 flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-start mb-4">
          <div>
            <h3 className="text-xl font-bold text-ui-dark">
              {teamName} — {payload?.exercise?.title || 'Exercise'}
            </h3>
            {payload?.exercise?.tutorial_title && (
              <div className="text-sm text-ui mt-0.5">
                {payload.exercise.tutorial_title}
              </div>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-ui hover:text-ui-dark text-2xl leading-none"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        {loading ? (
          <div className="text-ui py-8 text-center">Loading submissions…</div>
        ) : error ? (
          <div className="text-danger py-8 text-center">{error}</div>
        ) : submissions.length === 0 ? (
          <div className="text-ui py-8 text-center">
            No stored runs for this exercise (attempts that never executed keep
            no code).
          </div>
        ) : (
          <>
            <div className="h-[45vh] flex flex-col mb-4">
              <CodeHistoryViewer
                submissions={submissions}
                index={index}
                onIndexChange={setIndex}
                renderMeta={(sub) => (
                  <span
                    className={`text-xs font-semibold ${
                      sub?.passed ? 'text-green-600' : 'text-red-500'
                    }`}
                  >
                    {sub?.passed ? 'Passed' : 'Failed'}
                  </span>
                )}
              />
            </div>

            {/* Per-test results of the shown run — same renderer the student sees */}
            {current?.test_results?.length > 0 && (
              <ExerciseResults data={{ test_results: current.test_results }} />
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default ExerciseCodeModal;
