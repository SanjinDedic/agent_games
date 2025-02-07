import React, { useState, useEffect, useRef } from 'react';
import Editor from "@monaco-editor/react";
import ResultsDisplay from '../Utilities/ResultsDisplay';
import FeedbackSelector from '../Feedback/FeedbackSelector';
import { toast } from 'react-toastify';
import { useNavigate } from 'react-router-dom';
import UserTooltip from '../Utilities/UserTooltips';
import InstructionPopup from '../Utilities/InstructionPopup';
import { useDispatch, useSelector } from 'react-redux';
import { checkTokenExpiry } from '../../slices/authSlice';

function AgentSubmission() {
  const editorRef = useRef(null);
  const [code, setCode] = useState('');
  const [starterCode, setStarterCode] = useState('');
  const [lastSubmission, setLastSubmission] = useState('');
  const [hasLastSubmission, setHasLastSubmission] = useState(false);
  const dispatch = useDispatch();
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const currentLeague = useSelector((state) => state.leagues.currentLeague);
  const accessToken = useSelector((state) => state.auth.token);
  const currentUser = useSelector((state) => state.auth.currentUser);
  const isAuthenticated = useSelector((state) => state.auth.isAuthenticated);
  const [output, setOutput] = useState('');
  const [feedback, setFeedback] = useState('');
  const [instructionData, setInstructionData] = useState('');
  const [messageData, setMessageData] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const editorOptions = {
    minimap: { enabled: false },
    scrollbar: {
      vertical: 'auto',
      horizontal: 'auto'
    }
  };

  useEffect(() => {
    const tokenExpired = dispatch(checkTokenExpiry());
    if (!isAuthenticated || currentUser.role !== "student" || tokenExpired) {
      navigate('/AgentLogin');
    } else {
      loadLatestSubmission();
    }
  }, [navigate]);

  const loadLatestSubmission = async () => {
    try {
      const response = await fetch(`${apiUrl}/user/get-team-submission`, {
        headers: {
          'Authorization': `Bearer ${accessToken}`
        }
      });
      const data = await response.json();

      if (data.status === "success" && data.data && data.data.code) {
        setLastSubmission(data.data.code);
        setCode(data.data.code);
        setHasLastSubmission(true);
      } else {
        handleInstructions();
        setHasLastSubmission(false);
      }
    } catch (error) {
      console.error('Error loading submission:', error);
      handleInstructions();
      setHasLastSubmission(false);
    }
  };

  const handleInstructions = async () => {
    try {
      const response = await fetch(`${apiUrl}/user/get-game-instructions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ game_name: currentLeague.game }),
      });
      const data = await response.json();
      if (data.status === "success") {
        let code_sample = data.data.starter_code;
        code_sample = code_sample.slice(1);
        setCode(code_sample);
        setStarterCode(code_sample);
        setInstructionData(data.data.game_instructions);
      } else if (data.status === "error") {
        toast.error(data.message, { position: "top-center" });
      }
    } catch (error) {
      console.error('Error:', error);
      setIsLoading(false);
    }
  };

  const handleEditorDidMount = (editor) => {
    editorRef.current = editor;
  };

  const handleEditorChange = (value) => {
    setCode(value);
  };

  const handleSubmit = async () => {
    setOutput('');
    setFeedback('');
    setIsLoading(true);

    try {
      const response = await fetch(`${apiUrl}/user/submit-agent`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
        body: JSON.stringify({ code: code }),
      });
      const data = await response.json();
      if (data.status === "success") {
        setIsLoading(false);
        setOutput(data.data.results);
        setFeedback(data.data.feedback);
        setMessageData(data.message);
        loadLatestSubmission(); // Refresh last submission status
      } else if (data.status === "error") {
        toast.error(data.message, { position: "top-center" });
        setIsLoading(false);
      }
    } catch (error) {
      console.error('Error:', error);
      setIsLoading(false);
    }
  };

  const handleLoadLastSubmission = () => {
    if (hasLastSubmission && editorRef.current) {
      editorRef.current.setValue(lastSubmission);
      setCode(lastSubmission);
      toast.success('Loaded last submission', { position: "top-center" });
    }
  };

  const handleReset = () => {
    if (starterCode && editorRef.current) {
      editorRef.current.setValue(starterCode);
      setCode(starterCode);
      toast.success('Code reset to starter template', { position: "top-center" });
    } else {
      handleInstructions();
    }
  };

  return (
    <div className="min-h-screen pt-16 flex flex-col items-center bg-ui-lighter">
      <div className="w-full max-w-[1100px] px-4 shadow-md border border-primary/15 overflow-hidden">
        {/* Info Header */}
        <div className="bg-ui rounded-t-lg text-white grid grid-cols-3 gap-4 p-4 text-center">
          {currentUser.name && (
            <div className="text-lg font-medium">TEAM: {currentUser.name}</div>
          )}
          {currentLeague.game && (
            <div className="text-lg font-medium">GAME: {currentLeague.game}</div>
          )}
          {currentLeague.name && (
            <div className="text-lg font-medium">LEAGUE: {currentLeague.name}</div>
          )}
        </div>

        {/* Main Content */}
        <div className="bg-white rounded-b-lg shadow-lg p-6">
          <h1 className="text-2xl font-bold text-ui-dark mb-6 text-center">
            AGENT GAMES CODE SUBMISSION
          </h1>

          <InstructionPopup instructions={instructionData} homescreen={false} />

          {code && (
            <div className="mt-6">
              <Editor
                height="535px"
                width="100%"
                theme="vs-dark"
                defaultLanguage="python"
                value={code}
                onChange={handleEditorChange}
                onMount={handleEditorDidMount}
                options={editorOptions}
              />
            </div>
          )}

          <div className="mt-6 flex gap-4">
            <UserTooltip
              title="⚠️ INFO <br />Submit your code to see results below."
              arrow
              disableFocusListener
              disableTouchListener
            >
              <button
                onClick={handleSubmit}
                disabled={isLoading}
                className="flex-1 py-3 px-4 text-lg font-medium text-white bg-primary hover:bg-primary-hover disabled:bg-ui-light rounded-lg transition-colors duration-200"
              >
                {isLoading ? 'Submitting...' : 'Submit Code'}
              </button>
            </UserTooltip>

            <UserTooltip
              title="⚠️ INFO <br />Load your last submitted code."
              arrow
              disableFocusListener
              disableTouchListener
            >
              <button
                onClick={handleLoadLastSubmission}
                disabled={!hasLastSubmission || isLoading}
                className="flex-1 py-3 px-4 text-lg font-medium text-white bg-league-blue hover:bg-league-hover disabled:bg-ui-light rounded-lg transition-colors duration-200"
              >
                Last Submission
              </button>
            </UserTooltip>

            <UserTooltip
              title="⚠️ INFO <br />Reset your code to the original starter template."
              arrow
              disableFocusListener
              disableTouchListener
            >
              <button
                onClick={handleReset}
                disabled={isLoading}
                className="flex-1 py-3 px-4 text-lg font-medium text-white bg-notice-orange hover:bg-notice-orange/90 disabled:bg-ui-light rounded-lg transition-colors duration-200"
              >
                Reset Code
              </button>
            </UserTooltip>
          </div>

          {/* Results Section */}
          <div className="mt-8">
            {output ? (
              <>
                <ResultsDisplay
                  data={output}
                  data_message={messageData}
                  tablevisible={true}
                />
                {feedback && <FeedbackSelector feedback={feedback} />}
              </>
            ) : (
              <p className="text-center text-lg">
                {isLoading ? 'Loading results...' : 'Submit to see results'}
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default AgentSubmission;