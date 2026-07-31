import React, { useEffect } from "react";
import { useSelector } from "react-redux";
import { selectCurrentUser } from "../../slices/authSlice";
import CodeEditor from "../Shared/Submission/CodeEditor";
import CombinedFooter from "../Shared/Submission/CombinedFooter";
import ExerciseHints from "./ExerciseHints";
import FeedbackDisplay from "../Shared/Submission/FeedbackDisplay";
import MySubmissionsModal from "../Shared/Submission/MySubmissionsModal";
import OutputDrawer from "../Shared/Submission/OutputDrawer";
import SubmissionLayout from "../Shared/Submission/SubmissionLayout";
import ExerciseResults from "./ExerciseResults";
import usePyodideExerciseSubmit from "../Shared/hooks/usePyodideExerciseSubmit";
import useSubmissionWorkspace from "../Shared/hooks/useSubmissionWorkspace";
import useTutorialAPI from "../Shared/hooks/useTutorialAPI";
import { useTerms } from "../Shared/terminology";

/**
 * Submission workspace for one tutorial exercise. Mount it with
 * key={exercise.id} so switching exercises resets the editor and results.
 * `panelHeader` (optional) renders above the problem description — the
 * tutorial page uses it for the exercise picker.
 * `preview` (institution/teacher/admin) submits to the no-persist preview
 * endpoint and never touches the team-scoped submission history endpoints,
 * so every exercise opens on the starter code.
 */
function ExerciseSubmission({ exercise, tutorialTitle, panelHeader, preview = false }) {
  const currentUser = useSelector(selectCurrentUser);
  const T = useTerms();

  const { getLatestExerciseSubmission, getExerciseSubmissions } =
    useTutorialAPI();

  // Pyodide-first execution with automatic Celery fallback; same submitCode
  // contract as submitExercise, so the workspace is unchanged.
  const { submitCode, isLoading: isSubmitting } = usePyodideExerciseSubmit({
    exercise,
    preview,
  });

  const ws = useSubmissionWorkspace({
    getLatestSubmission: preview
      ? async () => ({ success: true, hasSubmission: false })
      : () => getLatestExerciseSubmission(exercise.id),
    getSubmissionHistory: preview
      ? async () => ({ success: true, submissions: [] })
      : () => getExerciseSubmissions(exercise.id),
    submitCode,
  });

  useEffect(() => {
    const loadInitialData = async () => {
      // Resume from the latest submission; fall back to the starter code
      const hadSubmission = await ws.loadLatestSubmission({ intoEditor: true });
      ws.applyStarterCode(exercise.starter_code || "", {
        intoEditor: !hadSubmission,
      });
    };

    loadInitialData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <SubmissionLayout
      editor={<CodeEditor {...ws.editorProps} />}
      editorDrawer={<OutputDrawer stdout={ws.stdout} isLoading={isSubmitting} />}
      panel={
        <>
          {panelHeader}
          <FeedbackDisplay
            instructions={exercise.problem_markdown}
            instructionsTitle="Problem Description"
            hintsPanel={
              <ExerciseHints
                hints={exercise.exercise_hints}
                exerciseId={exercise.id}
              />
            }
            hasResults={!!ws.output}
            isLoading={isSubmitting}
            collapseInstructions={ws.shouldCollapseInstructions}
            emptyTitle="Submit your code to see the test results here"
            emptySubtitle="Each test case will show whether it passed"
          >
            <ExerciseResults data={ws.output} showStdout={false} />
          </FeedbackDisplay>
        </>
      }
      footer={
        <CombinedFooter
          {...ws.footerProps}
          allowHint={false}
          isLoading={isSubmitting}
          statusItems={
            preview
              ? [{ label: "MODE", value: "Preview — code is not saved" }]
              : [{ label: T.Team.toUpperCase(), value: currentUser.name }]
          }
        />
      }
    >
      <MySubmissionsModal {...ws.submissionsModalProps} />
    </SubmissionLayout>
  );
}

export default ExerciseSubmission;
