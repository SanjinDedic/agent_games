import React, { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import ExerciseSubmission from "./ExerciseSubmission";
import TutorialOverview from "./TutorialOverview";
import useTutorialAPI from "../Shared/hooks/useTutorialAPI";

/**
 * Tutorial page. Two views driven by the `exercise` search param:
 * without it, an overview listing the tutorial's exercises in order with the
 * team's progress; with it, the selected exercise in the shared submission
 * workspace, with back/previous/next navigation in the panel header. Keeping
 * the selection in the URL makes refresh and browser-back behave.
 */
function Tutorial() {
  const { getTutorials, getTutorial, getTutorialProgress } = useTutorialAPI();
  const [searchParams, setSearchParams] = useSearchParams();

  const [tutorial, setTutorial] = useState(null);
  const [progressByExerciseId, setProgressByExerciseId] = useState({});
  const [loadError, setLoadError] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const selectedExerciseId = Number(searchParams.get("exercise")) || null;

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

  useEffect(() => {
    const loadTutorial = async () => {
      const listResult = await getTutorials();
      if (!listResult.success) {
        setLoadError(listResult.error);
        setIsLoading(false);
        return;
      }
      if (listResult.tutorials.length === 0) {
        setIsLoading(false);
        return;
      }

      const detailResult = await getTutorial(listResult.tutorials[0].id);
      if (!detailResult.success) {
        setLoadError(detailResult.error);
        setIsLoading(false);
        return;
      }

      setTutorial(detailResult.tutorial);
      setIsLoading(false);
    };

    loadTutorial();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Fetch progress whenever the overview is (re)shown, so an exercise passed
  // in the workspace is marked completed the moment the student comes back.
  useEffect(() => {
    if (tutorial && selectedExerciseId === null) {
      loadProgress(tutorial.id);
    }
  }, [tutorial, selectedExerciseId, loadProgress]);

  if (isLoading) {
    return (
      <div className="min-h-screen pt-12 flex items-center justify-center bg-white">
        <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-primary"></div>
        <span className="ml-3 text-ui-dark">Loading tutorial...</span>
      </div>
    );
  }

  if (loadError || !tutorial || tutorial.exercises.length === 0) {
    return (
      <div className="min-h-screen pt-12 flex items-center justify-center bg-white">
        <div className="text-center p-8 text-ui">
          <p className="text-xl">
            {loadError || "No tutorial is available yet."}
          </p>
          <p className="text-sm mt-2">
            {loadError
              ? "Please try again later."
              : "Check back soon — exercises are on the way."}
          </p>
        </div>
      </div>
    );
  }

  const exercises = tutorial.exercises; // already in order_index order
  const selectedIndex = exercises.findIndex((e) => e.id === selectedExerciseId);

  const showExercise = (exerciseId) =>
    setSearchParams({ exercise: String(exerciseId) });
  const showOverview = () => setSearchParams({});

  if (selectedIndex === -1) {
    return (
      <TutorialOverview
        tutorial={tutorial}
        progressByExerciseId={progressByExerciseId}
        onSelectExercise={showExercise}
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
