import React, { useState, useEffect, useRef } from "react";
import { useDispatch, useSelector } from "react-redux";
import { toast } from "react-toastify";
import { selectCurrentUser } from "../../slices/authSlice";
import { setCurrentLeague } from "../../slices/leaguesSlice";
import CodeEditor from "./CodeEditor";
import CombinedFooter from "./CombinedFooter";
import FeedbackDisplay from "./FeedbackDisplay";
import MySubmissionsModal from "./MySubmissionsModal";
import HintModal from "./HintModal";
import useSubmissionAPI from "../Shared/hooks/useSubmissionAPI";
import useLeagueAPI from "../Shared/hooks/useLeagueAPI";

function AgentSubmission() {
  // State management
  const [code, setCode] = useState("");
  const [starterCode, setStarterCode] = useState("");
  const [lastSubmission, setLastSubmission] = useState("");
  const [output, setOutput] = useState("");
  const [feedback, setFeedback] = useState("");
  const [instructionData, setInstructionData] = useState("");
  const [hasLastSubmission, setHasLastSubmission] = useState(false);
  const [shouldCollapseInstructions, setShouldCollapseInstructions] =
    useState(false);
  const [isLoadingLeagueInfo, setIsLoadingLeagueInfo] = useState(false);
  const [submissionsModalOpen, setSubmissionsModalOpen] = useState(false);
  const [submissionHistory, setSubmissionHistory] = useState([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [hintModalOpen, setHintModalOpen] = useState(false);
  const [hint, setHint] = useState(null);
  const [isGeneratingHint, setIsGeneratingHint] = useState(false);
  const [allowHint, setAllowHint] = useState(false);
  // Code as it was at the last submit attempt (success or fail) — gates the hint button
  const [lastSubmittedCode, setLastSubmittedCode] = useState(null);
  const editorRef = useRef(null);

  // Redux hooks
  const dispatch = useDispatch();
  const currentLeague = useSelector((state) => state.leagues.currentLeague);
  const currentUser = useSelector(selectCurrentUser);

  // Custom API hooks
  const {
    getLatestSubmission,
    getTeamSubmissions,
    getGameInstructions,
    submitCode,
    isLoading: isSubmitting,
  } = useSubmissionAPI();

  const { fetchUserLeagues, isLoading: isLeagueLoading } = useLeagueAPI();

  // Combined loading state
  const isLoading = isSubmitting || isLeagueLoading || isLoadingLeagueInfo;

  useEffect(() => {
    const loadInitialData = async () => {
      // Load the latest submission
      let hadSubmission = false;
      const submissionResult = await getLatestSubmission();
      if (submissionResult.success) {
        if (submissionResult.hasSubmission) {
          setLastSubmission(submissionResult.code);
          setCode(submissionResult.code);
          setHasLastSubmission(true);
          hadSubmission = true;
        } else {
          setHasLastSubmission(false);
        }
      }

      // If currentLeague exists but is missing the game property, fetch league details
      if (currentLeague && !currentLeague.game) {
        setIsLoadingLeagueInfo(true);
        const leaguesResult = await fetchUserLeagues();
        setIsLoadingLeagueInfo(false);

        if (leaguesResult.success && leaguesResult.leagues?.length > 0) {
          // Find our league and update current league in Redux if needed
          const league = leaguesResult.leagues.find(
            (l) => l.id === currentLeague.id || l.name === currentLeague.name
          );

          if (league && league.game) {
            dispatch(setCurrentLeague(league.name));
            await loadInstructions(league.game, hadSubmission);
          }
        }
      }
      // If we already have the game info, load instructions directly
      else if (currentLeague && currentLeague.game) {
        await loadInstructions(currentLeague.game, hadSubmission);
      }
    };

    loadInitialData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Load game instructions and starter code
  const loadInstructions = async (gameOverride = null, hasSubmissionOverride = null) => {
    const gameToUse = gameOverride || (currentLeague && currentLeague.game);
    if (!gameToUse) return;

    const result = await getGameInstructions(gameToUse);

    if (result.success) {
      setInstructionData(result.instructions || "");

      if (result.starterCode) {
        setStarterCode(result.starterCode);
        const hasSub = hasSubmissionOverride !== null ? hasSubmissionOverride : hasLastSubmission;
        if (!hasSub) {
          setCode(result.starterCode);
        }
      }
    }
  };

  // Submit code to the API
  const handleSubmit = async () => {
    if (!code || code.trim() === "") {
      toast.error("Please enter some code before submitting");
      return;
    }

    setOutput("");
    setFeedback("");
    setShouldCollapseInstructions(true);
    setLastSubmittedCode(code);

    const result = await submitCode(code);
    if (result.hint_available && !allowHint) toast.success("A hint is now available");
    setAllowHint(result.hint_available);

    if (result.success) {
      setOutput(result.output);
      setFeedback(result.feedback);

      // Refresh the latest submission info
      const refreshResult = await getLatestSubmission();
      if (refreshResult.success && refreshResult.hasSubmission) {
        setLastSubmission(refreshResult.code);
        setHasLastSubmission(true);
      }
    }
  };

  // Request a hint for the current code (hits the same endpoint with generate_hint=true)
  const handleGetHint = async () => {
    if (!code || code.trim() === "") {
      toast.error("Please enter some code before requesting a hint");
      return;
    }

    setIsGeneratingHint(true);
    setHint(null);
    setHintModalOpen(true);

    setLastSubmittedCode(code);
    const result = await submitCode(code, { generateHint: true });

    setIsGeneratingHint(false);

    if (result.hint_available && !allowHint) toast.success("A hint is now available");
    setAllowHint(result.hint_available);

    // A hint only comes back when validation fails — hints exist to help
    // students reach valid code, not to improve a valid agent.
    if (result.hint) {
      setHint(result.hint);
    } else {
      if (result.hint_cancelled) {
        // The edited code passed validation, so no hint was generated or consumed
        toast.success("Submission valid — hint cancelled");
      }
      // otherwise submitCode already surfaced the error via toast
      setHintModalOpen(false);
    }

    if (result.success) {
      // The hint request is a real submission, so refresh the feedback panel too
      setOutput(result.output);
      setFeedback(result.feedback);
      setShouldCollapseInstructions(true);

      const refreshResult = await getLatestSubmission();
      if (refreshResult.success && refreshResult.hasSubmission) {
        setLastSubmission(refreshResult.code);
        setHasLastSubmission(true);
      }
    }
  };

  // Load last submitted code
  const handleLoadLastSubmission = () => {
    if (hasLastSubmission && editorRef.current) {
      editorRef.current.setValue(lastSubmission);
      setCode(lastSubmission);
      toast.success("Loaded last submission");
    } else {
      toast.error("No previous submission found");
    }
  };

  // Open submissions modal and load history
  const handleShowSubmissions = async () => {
    setSubmissionsModalOpen(true);
    setIsLoadingHistory(true);
    const result = await getTeamSubmissions();
    setIsLoadingHistory(false);
    if (result.success) {
      setSubmissionHistory(result.submissions);
    } else {
      toast.error(result.error || "Failed to load submissions");
      setSubmissionHistory([]);
    }
  };

  // Load a specific past submission into the editor
  const handleSelectSubmission = (sub) => {
    if (editorRef.current && sub?.code != null) {
      editorRef.current.setValue(sub.code);
      setCode(sub.code);
      setSubmissionsModalOpen(false);
      toast.success("Submission loaded into editor");
    }
  };

  // Reset code to starter template
  const handleReset = () => {
    if (starterCode && editorRef.current) {
      editorRef.current.setValue(starterCode);
      setCode(starterCode);
      toast.success("Code reset to starter template");
    } else {
      toast.error("Starter code template not available");
      // Try to load instructions again
      const gameToUse = currentLeague && currentLeague.game;
      if (gameToUse) {
        loadInstructions(gameToUse);
      }
    }
  };

  // Update editor reference when mounted
  const handleEditorDidMount = (editor) => {
    editorRef.current = editor;
  };

  return (
    <div className="min-h-screen pt-12 flex flex-col bg-white">
      <div className="flex flex-1 overflow-hidden pb-14">
        {/* Left side - Code Editor */}
        <div className="w-1/2 h-[calc(100vh-112px)] border-r border-[#1e1e1e] border-t-0 bg-[#1e1e1e]">
          <CodeEditor
            code={code}
            onCodeChange={setCode}
            onMount={handleEditorDidMount}
          />
        </div>

        {/* Right side - Feedback */}
        <div className="w-1/2 flex flex-col h-[calc(100vh-112px)]">
          {/* Feedback Display */}
          <div className="flex-1 overflow-auto">
            <FeedbackDisplay
              instructions={instructionData}
              output={output}
              feedback={feedback}
              isLoading={isLoading}
              collapseInstructions={shouldCollapseInstructions}
            />
          </div>
        </div>
      </div>

      {/* Combined Footer */}
      <CombinedFooter
        team={currentUser.name}
        game={currentLeague?.game}
        league={currentLeague?.name}
        isDemo={currentUser.is_demo}
        onSubmit={handleSubmit}
        onGetHint={handleGetHint}
        onLoadLast={handleLoadLastSubmission}
        onReset={handleReset}
        onShowSubmissions={handleShowSubmissions}
        isLoading={isLoading}
        allowHint={allowHint}
        codeChangedSinceLastSubmit={lastSubmittedCode !== null && code !== lastSubmittedCode}
        isGeneratingHint={isGeneratingHint}
        hasLastSubmission={hasLastSubmission}
        hasStarterCode={!!starterCode}
      />

      <MySubmissionsModal
        isOpen={submissionsModalOpen}
        onClose={() => setSubmissionsModalOpen(false)}
        submissions={submissionHistory}
        isLoading={isLoadingHistory}
        onSelect={handleSelectSubmission}
      />

      <HintModal
        isOpen={hintModalOpen}
        isLoading={isGeneratingHint}
        hint={hint}
        onClose={() => setHintModalOpen(false)}
      />
    </div>
  );
}

export default AgentSubmission;
