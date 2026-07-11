import React from "react";

/**
 * Landing view for the tutorial: title, description, overall progress, and
 * the exercises as an ordered list in teaching order. Each row shows the
 * team's status (completed / in progress / not started) and opens the
 * exercise workspace via onSelectExercise.
 */
function TutorialOverview({ tutorial, progressByExerciseId, onSelectExercise }) {
  const exercises = tutorial.exercises;
  const passedCount = exercises.filter(
    (exercise) => progressByExerciseId[exercise.id]?.passed
  ).length;
  const percentComplete =
    exercises.length > 0 ? (passedCount / exercises.length) * 100 : 0;

  return (
    <div className="min-h-screen pt-16 pb-12 bg-ui-lighter">
      <div className="max-w-3xl mx-auto px-4">
        <div className="bg-white rounded-lg shadow border border-ui-light/30 p-6">
          <h1 className="text-2xl font-bold text-ui-dark">{tutorial.title}</h1>
          {tutorial.description && (
            <p className="mt-2 text-ui-dark/70">{tutorial.description}</p>
          )}
          <div className="mt-4">
            <div className="flex justify-between text-sm text-ui-dark/70 mb-1">
              <span>
                {passedCount} of {exercises.length} exercises completed
              </span>
              <span>{Math.round(percentComplete)}%</span>
            </div>
            <div className="h-2 rounded-full bg-ui-lighter overflow-hidden">
              <div
                className="h-full rounded-full bg-success transition-all duration-400"
                style={{ width: `${percentComplete}%` }}
              />
            </div>
          </div>
        </div>

        <ol className="mt-6 space-y-3">
          {exercises.map((exercise, idx) => {
            const progress = progressByExerciseId[exercise.id];
            const status = progress?.passed
              ? "completed"
              : progress?.attempted
                ? "in-progress"
                : "not-started";

            return (
              <li key={exercise.id}>
                <button
                  onClick={() => onSelectExercise(exercise.id)}
                  className="w-full flex items-center gap-4 bg-white rounded-lg shadow border border-ui-light/30 p-4 text-left transition-colors hover:border-primary/60 hover:bg-primary/5"
                >
                  <span
                    className={`flex-shrink-0 flex items-center justify-center w-9 h-9 rounded-full font-bold ${
                      status === "completed"
                        ? "bg-success text-white"
                        : status === "in-progress"
                          ? "bg-notice-orange text-white"
                          : "bg-ui-lighter text-ui-dark"
                    }`}
                  >
                    {status === "completed" ? "✓" : idx + 1}
                  </span>
                  <span className="flex-1 min-w-0">
                    <span className="block font-medium text-ui-dark">
                      {exercise.title}
                    </span>
                    <span
                      className={`block text-sm ${
                        status === "completed"
                          ? "text-success"
                          : status === "in-progress"
                            ? "text-notice-orange"
                            : "text-ui-dark/50"
                      }`}
                    >
                      {status === "completed"
                        ? "Completed"
                        : status === "in-progress"
                          ? "In progress"
                          : "Not started"}
                    </span>
                  </span>
                  <span className="text-ui-dark/40" aria-hidden="true">
                    →
                  </span>
                </button>
              </li>
            );
          })}
        </ol>
      </div>
    </div>
  );
}

export default TutorialOverview;
