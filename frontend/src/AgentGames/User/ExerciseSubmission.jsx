import React, { useEffect } from "react";
import { useSelector } from "react-redux";
import { selectCurrentUser } from "../../slices/authSlice";
import CodeEditor from "../Shared/Submission/CodeEditor";
import CombinedFooter from "../Shared/Submission/CombinedFooter";
import ExerciseHints from "./ExerciseHints";
import FeedbackDisplay from "../Shared/Submission/FeedbackDisplay";
import MySubmissionsModal from "../Shared/Submission/MySubmissionsModal";
import SubmissionLayout from "../Shared/Submission/SubmissionLayout";
import ExerciseResults from "./ExerciseResults";
import useSubmissionWorkspace from "../Shared/hooks/useSubmissionWorkspace";
import useTutorialAPI from "../Shared/hooks/useTutorialAPI";
import { useTerms } from "../Shared/terminology";

/**
 * Submission workspace for one tutorial exercise. Mount it with
 * key={exercise.id} so switching exercises resets the editor and results.
 * `panelHeader` (optional) renders above the problem description — the
 * tutorial page uses it for the exercise picker.
 */
function ExerciseSubmission({ exercise, tutorialTitle, panelHeader }) {
  const currentUser = useSelector(selectCurrentUser);
  const T = useTerms();

  const {
    getLatestExerciseSubmission,
    getExerciseSubmissions,
    submitExercise,
    isLoading: isSubmitting,
  } = useTutorialAPI();

  const ws = useSubmissionWorkspace({
    getLatestSubmission: () => getLatestExerciseSubmission(exercise.id),
    getSubmissionHistory: () => getExerciseSubmissions(exercise.id),
    submitCode: (code) => submitExercise(exercise.id, code),
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
      panel={
        <>
          {panelHeader}
          <FeedbackDisplay
            instructions={exercise.problem_markdown}
            instructionsTitle="Problem Description"
            hintsPanel={<ExerciseHints hints={exercise.exercise_hints} />}
            hasResults={!!ws.output}
            isLoading={isSubmitting}
            collapseInstructions={ws.shouldCollapseInstructions}
            emptyTitle="Submit your code to see the test results here"
            emptySubtitle="Each test case will show whether it passed"
          >
            <ExerciseResults data={ws.output} />
          </FeedbackDisplay>
        </>
      }
      footer={
        <CombinedFooter
          {...ws.footerProps}
          allowHint={false}
          isLoading={isSubmitting}
          statusItems={[
            { label: T.Team.toUpperCase(), value: currentUser.name },
          ]}
        />
      }
    >
      <MySubmissionsModal {...ws.submissionsModalProps} />
    </SubmissionLayout>
  );
}

export default ExerciseSubmission;
