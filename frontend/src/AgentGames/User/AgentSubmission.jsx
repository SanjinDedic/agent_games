import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import { toast } from "react-toastify";
import { checkTokenExpiry } from "../../slices/authSlice";
import { setCurrentLeague } from "../../slices/leaguesSlice";
import CodeEditor from "./CodeEditor";
import CombinedFooter from "./CombinedFooter";
import FeedbackDisplay from "./FeedbackDisplay";
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
  const editorRef = useRef(null);

  // Redux hooks
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const currentLeague = useSelector((state) => state.leagues.currentLeague);
  const currentUser = useSelector((state) => state.auth.currentUser);
  const isAuthenticated = useSelector((state) => state.auth.isAuthenticated);

  // Custom API hooks
  const {
    getLatestSubmission,
    getGameInstructions,
    submitCode,
    isLoading: isSubmitting,
  } = useSubmissionAPI();

  const { fetchUserLeagues, isLoading: isLeagueLoading } = useLeagueAPI();

  // Combined loading state
  const isLoading = isSubmitting || isLeagueLoading || isLoadingLeagueInfo;

  // Check authentication and load necessary data
  useEffect(() => {
    const tokenExpired = dispatch(checkTokenExpiry());
    if (!isAuthenticated || currentUser.role !== "student" || tokenExpired) {
      navigate("/AgentLogin");
      return;
    }

    const loadInitialData = async () => {
      // Load the latest submission
      const submissionResult = await getLatestSubmission();
      if (submissionResult.success) {
        if (submissionResult.hasSubmission) {
          setLastSubmission(submissionResult.code);
          setCode(submissionResult.code);
          setHasLastSubmission(true);
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
            await loadInstructions(league.game);
          }
        }
      }
      // If we already have the game info, load instructions directly
      else if (currentLeague && currentLeague.game) {
        await loadInstructions(currentLeague.game);
      }
    };

    loadInitialData();
  }, [navigate, dispatch, isAuthenticated, currentUser, currentLeague]); // Removed API functions from deps

  // Load game instructions and starter code
  const loadInstructions = async (gameOverride = null) => {
    const gameToUse = gameOverride || (currentLeague && currentLeague.game);
    if (!gameToUse) return;

    const result = await getGameInstructions(gameToUse);

    if (result.success) {
      setInstructionData(result.instructions || "");

      if (result.starterCode) {
        setStarterCode(result.starterCode);
        if (!hasLastSubmission) {
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

    const result = await submitCode(code);

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
        onLoadLast={handleLoadLastSubmission}
        onReset={handleReset}
        isLoading={isLoading}
        hasLastSubmission={hasLastSubmission}
        hasStarterCode={!!starterCode}
      />
    </div>
  );
}

export default AgentSubmission;