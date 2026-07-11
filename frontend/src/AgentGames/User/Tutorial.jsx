import React, { useEffect, useState } from "react";
import ExerciseSubmission from "./ExerciseSubmission";
import useTutorialAPI from "../Shared/hooks/useTutorialAPI";

/**
 * Tutorial page: loads the first tutorial with its ordered exercises and
 * shows the selected exercise in the shared submission workspace. The
 * exercise picker renders inside the workspace's right-hand panel.
 */
function Tutorial() {
  const { getTutorials, getTutorial } = useTutorialAPI();

  const [tutorial, setTutorial] = useState(null);
  const [selectedExerciseId, setSelectedExerciseId] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

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
      setSelectedExerciseId(detailResult.tutorial.exercises[0]?.id ?? null);
      setIsLoading(false);
    };

    loadTutorial();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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

  const selectedExercise =
    tutorial.exercises.find((e) => e.id === selectedExerciseId) ||
    tutorial.exercises[0];

  return (
    <ExerciseSubmission
      key={selectedExercise.id}
      exercise={selectedExercise}
      tutorialTitle={tutorial.title}
      panelHeader={
        <div className="mx-4 mt-4 bg-white rounded-lg shadow border border-ui-light/30 p-4">
          <h1 className="text-xl font-bold text-ui-dark">{tutorial.title}</h1>
          {tutorial.description && (
            <p className="mt-1 text-sm text-ui-dark/70">
              {tutorial.description}
            </p>
          )}
          {tutorial.exercises.length > 1 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {tutorial.exercises.map((exercise, idx) => (
                <button
                  key={exercise.id}
                  onClick={() => setSelectedExerciseId(exercise.id)}
                  className={`py-1 px-3 text-sm rounded-full transition-colors ${
                    exercise.id === selectedExercise.id
                      ? "bg-primary text-white"
                      : "bg-ui-lighter text-ui-dark hover:bg-ui-light/50"
                  }`}
                >
                  {idx + 1}. {exercise.title}
                </button>
              ))}
            </div>
          )}
        </div>
      }
    />
  );
}

export default Tutorial;
