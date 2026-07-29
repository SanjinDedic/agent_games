import React, { useState, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { selectCurrentUser, selectLeagueId } from "../../slices/authSlice";
import { setCurrentLeague } from "../../slices/leaguesSlice";
import CodeEditor from "../Shared/Submission/CodeEditor";
import CombinedFooter from "../Shared/Submission/CombinedFooter";
import FeedbackDisplay from "../Shared/Submission/FeedbackDisplay";
import MySubmissionsModal from "../Shared/Submission/MySubmissionsModal";
import HintModal from "../Shared/Submission/HintModal";
import SubmissionLayout from "../Shared/Submission/SubmissionLayout";
import FeedbackSelector from "../Feedback/FeedbackSelector";
import GameResultsWrapper from "../Feedback/GameResultsWrapper";
import useSubmissionWorkspace from "../Shared/hooks/useSubmissionWorkspace";
import useSubmissionAPI from "../Shared/hooks/useSubmissionAPI";
import useLeagueAPI from "../Shared/hooks/useLeagueAPI";
import { useTerms } from "../Shared/terminology";

function AgentSubmission() {
  const T = useTerms();
  // Agent-specific state: game instructions and league resolution
  const [instructionData, setInstructionData] = useState("");
  const [isLoadingLeagueInfo, setIsLoadingLeagueInfo] = useState(false);

  // Redux hooks
  const dispatch = useDispatch();
  const currentLeague = useSelector((state) => state.leagues.currentLeague);
  const currentUser = useSelector(selectCurrentUser);
  const assignedLeagueId = useSelector(selectLeagueId);

  // Custom API hooks
  const {
    getLatestSubmission,
    getTeamSubmissions,
    getGameInstructions,
    submitCode,
    isLoading: isSubmitting,
  } = useSubmissionAPI();

  const { fetchUserLeagues, isLoading: isLeagueLoading } = useLeagueAPI();

  // Shared editor/submission state and handlers
  const ws = useSubmissionWorkspace({
    getLatestSubmission,
    getSubmissionHistory: getTeamSubmissions,
    submitCode,
    onResetUnavailable: () => loadInstructions(),
  });

  // Combined loading state
  const isLoading = isSubmitting || isLeagueLoading || isLoadingLeagueInfo;

  useEffect(() => {
    const loadInitialData = async () => {
      // Load the latest submission into the editor
      const hadSubmission = await ws.loadLatestSubmission({ intoEditor: true });

      // The workspace has to resolve its own league: students arrive here
      // straight from /TeamHome or the navbar, and neither fills the leagues
      // slice — only the league picker and the signup pages do. Without a
      // league there is no game, and so no instructions and no starter code.
      let game = currentLeague?.game || null;

      if (!game) {
        setIsLoadingLeagueInfo(true);
        const leaguesResult = await fetchUserLeagues();
        setIsLoadingLeagueInfo(false);

        if (leaguesResult.success && leaguesResult.leagues?.length > 0) {
          // Prefer the league the token says we're assigned to; fall back to
          // whatever partial record Redux already held.
          const league =
            leaguesResult.leagues.find((l) => l.id === assignedLeagueId) ||
            (currentLeague &&
              leaguesResult.leagues.find(
                (l) => l.id === currentLeague.id || l.name === currentLeague.name
              ));

          if (league && league.game) {
            dispatch(setCurrentLeague(league.name));
            game = league.game;
          }
        }
      }

      if (game) {
        await loadInstructions(game, hadSubmission);
      }
    };

    loadInitialData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Load game instructions and starter code
  async function loadInstructions(gameOverride = null, hasSubmissionOverride = null) {
    const gameToUse = gameOverride || (currentLeague && currentLeague.game);
    if (!gameToUse) return;

    const result = await getGameInstructions(gameToUse);

    if (result.success) {
      setInstructionData(result.instructions || "");

      if (result.starterCode) {
        const hasSub =
          hasSubmissionOverride !== null
            ? hasSubmissionOverride
            : ws.hasLastSubmission;
        ws.applyStarterCode(result.starterCode, { intoEditor: !hasSub });
      }
    }
  }

  return (
    <SubmissionLayout
      editor={<CodeEditor {...ws.editorProps} />}
      panel={
        <FeedbackDisplay
          instructions={instructionData}
          hasResults={!!ws.output}
          isLoading={isLoading}
          collapseInstructions={ws.shouldCollapseInstructions}
        >
          <GameResultsWrapper data={ws.output} tablevisible={true} />
          {ws.feedback && <FeedbackSelector feedback={ws.feedback} />}
        </FeedbackDisplay>
      }
      footer={
        <CombinedFooter
          {...ws.footerProps}
          isLoading={isLoading}
          statusItems={[
            { label: T.Team.toUpperCase(), value: currentUser.name },
            { label: "GAME", value: currentLeague?.game },
            { label: T.League.toUpperCase(), value: currentLeague?.name },
          ]}
        />
      }
    >
      <MySubmissionsModal {...ws.submissionsModalProps} />
      <HintModal {...ws.hintModalProps} />
    </SubmissionLayout>
  );
}

export default AgentSubmission;
