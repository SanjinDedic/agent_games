import React, { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import ExerciseSubmission from "./ExerciseSubmission";
import TutorialOverview from "./TutorialOverview";
import useTutorialAPI from "../Shared/hooks/useTutorialAPI";

/**
 * Tutorial page. The backend only returns the tutorials attached to the
 * team's league, so the page adapts to how many there are:
 * - none: an empty state
 * - one: straight into that tutorial (today's behaviour)
 * - many: a picker list first, with the chosen tutorial in the `tutorial`
 *   search param
 * Within a tutorial the `exercise` search param drives overview vs. exercise
 * workspace, as before. Keeping both selections in the URL makes refresh and
 * browser-back behave.
 */
function Tutorial() {
  const { getTutorials, getTutorial, getTutorialProgress } = useTutorialAPI();
  const [searchParams, setSearchParams] = useSearchParams();

  const [tutorials, setTutorials] = useState(null); // null = list loading
  const [tutorial, setTutorial] = useState(null);
  const [progressByExerciseId, setProgressByExerciseId] = useState({});
  const [loadError, setLoadError] = useState(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);

  const selectedTutorialId = Number(searchParams.get("tutorial")) || null;
  const selectedExerciseId = Number(searchParams.get("exercise")) || null;

  // With exactly one tutorial there is nothing to pick: open it directly.
  const effectiveTutorialId =
    selectedTutorialId ??
    (tutorials && tutorials.length === 1 ? tutorials[0].id : null);

  useEffect(() => {
    const loadList = async () => {
      const result = await getTutorials();
      if (result.success) {
        setTutorials(result.tutorials);
      } else {
        setLoadError(result.error);
        setTutorials([]);
      }
    };
    loadList();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!effectiveTutorialId) {
      setTutorial(null);
      return;
    }
    let cancelled = false;
    const loadDetail = async () => {
      setIsLoadingDetail(true);
      const result = await getTutorial(effectiveTutorialId);
      if (cancelled) return;
      if (result.success) {
        setTutorial(result.tutorial);
      } else {
        setLoadError(result.error);
      }
      setIsLoadingDetail(false);
    };
    loadDetail();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [effectiveTutorialId]);

  const loadProgress = useCallback(
    async (tutorialId) => {
      const result = await getTutorialProgress(tutorialId);
      if (result.success) {
        setProgressByExerciseId(
          Object.fromEntries(result.progress.map((p) => [p.exercise_id, p]))
        );
      }
    },
    [getTutorialProgress]
  );

  // Fetch progress whenever the overview is (re)shown, so an exercise passed
  // in the workspace is marked completed the moment the student comes back.
  useEffect(() => {
    if (tutorial && selectedExerciseId === null) {
      loadProgress(tutorial.id);
    }
  }, [tutorial, selectedExerciseId, loadProgress]);

  if (tutorials === null || (effectiveTutorialId && isLoadingDetail && !tutorial)) {
    return (
      <div className="min-h-screen pt-12 flex items-center justify-center bg-white">
        <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-primary"></div>
        <span className="ml-3 text-ui-dark">Loading tutorial...</span>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="min-h-screen pt-12 flex items-center justify-center bg-white">
        <div className="text-center p-8 text-ui">
          <p className="text-xl">{loadError}</p>
          <p className="text-sm mt-2">Please try again later.</p>
        </div>
      </div>
    );
  }

  if (tutorials.length === 0) {
    return (
      <div className="min-h-screen pt-12 flex items-center justify-center bg-white">
        <div className="text-center p-8 text-ui">
          <p className="text-xl">Your league doesn't have any tutorials yet.</p>
          <p className="text-sm mt-2">
            Check back soon — your teacher can add tutorials to the league.
          </p>
        </div>
      </div>
    );
  }

  const showTutorial = (tutorialId) =>
    setSearchParams({ tutorial: String(tutorialId) });
  const showTutorialList = () => setSearchParams({});

  // Multiple tutorials and none chosen (or a stale id not in this league):
  // show the picker.
  if (
    !effectiveTutorialId ||
    !tutorials.some((t) => t.id === effectiveTutorialId)
  ) {
    return (
      <div className="min-h-screen pt-16 pb-12 bg-ui-lighter">
        <div className="max-w-3xl mx-auto px-4">
          <div className="bg-white rounded-lg shadow border border-ui-light/30 p-6">
            <h1 className="text-2xl font-bold text-ui-dark">Tutorials</h1>
            <p className="mt-2 text-ui-dark/70">
              Pick a tutorial to work through its exercises.
            </p>
          </div>
          <ul className="mt-6 space-y-3">
            {tutorials.map((item) => (
              <li key={item.id}>
                <button
                  onClick={() => showTutorial(item.id)}
                  className="w-full flex items-center gap-4 bg-white rounded-lg shadow border border-ui-light/30 p-4 text-left transition-colors hover:border-primary/60 hover:bg-primary/5"
                >
                  <span className="flex-1 min-w-0">
                    <span className="block font-medium text-ui-dark">
                      {item.title}
                    </span>
                    {item.description && (
                      <span className="block text-sm text-ui-dark/60 truncate">
                        {item.description}
                      </span>
                    )}
                    <span className="block text-sm text-ui-dark/50 mt-1">
                      {item.exercise_count}{" "}
                      {item.exercise_count === 1 ? "exercise" : "exercises"}
                    </span>
                  </span>
                  <span className="text-ui-dark/40" aria-hidden="true">
                    →
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      </div>
    );
  }

  if (!tutorial) {
    return (
      <div className="min-h-screen pt-12 flex items-center justify-center bg-white">
        <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-primary"></div>
        <span className="ml-3 text-ui-dark">Loading tutorial...</span>
      </div>
    );
  }

  if (tutorial.exercises.length === 0) {
    return (
      <div className="min-h-screen pt-12 flex items-center justify-center bg-white">
        <div className="text-center p-8 text-ui">
          <p className="text-xl">This tutorial has no exercises yet.</p>
          <p className="text-sm mt-2">
            Check back soon — exercises are on the way.
          </p>
          {tutorials.length > 1 && (
            <button
              onClick={showTutorialList}
              className="mt-4 py-2 px-4 rounded bg-ui-lighter text-ui-dark hover:bg-ui-light/50 transition-colors"
            >
              ← All tutorials
            </button>
          )}
        </div>
      </div>
    );
  }

  const exercises = tutorial.exercises; // already in order_index order
  const selectedIndex = exercises.findIndex((e) => e.id === selectedExerciseId);

  const showExercise = (exerciseId) =>
    setSearchParams({
      tutorial: String(tutorial.id),
      exercise: String(exerciseId),
    });
  const showOverview = () => setSearchParams({ tutorial: String(tutorial.id) });

  if (selectedIndex === -1) {
    return (
      <TutorialOverview
        tutorial={tutorial}
        progressByExerciseId={progressByExerciseId}
        onSelectExercise={showExercise}
        onBackToList={tutorials.length > 1 ? showTutorialList : null}
      />
    );
  }

  const selectedExercise = exercises[selectedIndex];
  const previousExercise = exercises[selectedIndex - 1];
  const nextExercise = exercises[selectedIndex + 1];
  const navButtonClass =
    "py-1 px-3 text-sm rounded bg-ui-lighter text-ui-dark hover:bg-ui-light/50 transition-colors disabled:opacity-40 disabled:cursor-not-allowed";

  return (
    <ExerciseSubmission
      key={selectedExercise.id}
      exercise={selectedExercise}
      tutorialTitle={tutorial.title}
      panelHeader={
        <div className="mx-4 mt-4 bg-white rounded-lg shadow border border-ui-light/30 p-3 flex items-center gap-3">
          <button onClick={showOverview} className={navButtonClass}>
            ← All exercises
          </button>
          <span className="flex-1 min-w-0 truncate text-sm text-ui-dark">
            <span className="font-medium">
              {selectedIndex + 1}. {selectedExercise.title}
            </span>
            <span className="text-ui-dark/50"> — {selectedIndex + 1} of {exercises.length}</span>
          </span>
          <button
            onClick={() => showExercise(previousExercise.id)}
            disabled={!previousExercise}
            className={navButtonClass}
          >
            ← Previous
          </button>
          <button
            onClick={() => showExercise(nextExercise.id)}
            disabled={!nextExercise}
            className={navButtonClass}
          >
            Next →
          </button>
        </div>
      }
    />
  );
}

export default Tutorial;
