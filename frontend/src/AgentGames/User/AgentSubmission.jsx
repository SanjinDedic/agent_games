import React, { useState, useEffect, useRef } from 'react';
import Editor from "@monaco-editor/react";
import { constrainedEditor } from "constrained-editor-plugin";
import ResultsDisplay from '../Utilities/ResultsDisplay';
import MarkdownFeedback from '../Utilities/MarkdownFeedback';
import { toast } from 'react-toastify';
import { useNavigate } from 'react-router-dom';
import './css/submission.css'
import UserTooltip from '../Utilities/UserTooltips';
import InstructionPopup from '../Utilities/InstructionPopup';
import { useDispatch, useSelector } from 'react-redux';
import { checkTokenExpiry } from '../../slices/authSlice';

const AgentSubmission = () => {
  const monacoRef = useRef(null);
  const [code, setCode] = useState('');
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
  const restrictions = [];
  const navigate = useNavigate();
  const editorOptions = {
    minimap: { enabled: false }, // This disables the minimap
    scrollbar: {
      vertical: 'auto',
      horizontal: 'auto'
    }
  };
  useEffect(() => {
    const tokenExpired = dispatch(checkTokenExpiry());
    handleInstructions();
    if (!isAuthenticated || currentUser.role !== "student" || tokenExpired) {
      // Redirect to the home page if not authenticated
      navigate('/AgentLogin');
    }

  }, [navigate]);


  const handleInstructions = async () => {
    try {
      const response = await fetch(`${apiUrl}/get_game_instructions`, {
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
        setInstructionData(data.data.game_instructions);
      } else if (data.status === "error") {
        toast.error(data.message, { position: "top-center" });
      } else if (data.detail) {
        toast.error(data.detail, { position: "top-center" });
      }
    } catch (error) {
      console.error('Error:', error);
      setIsLoading(false);
    }
  };

  const handleEditorDidMount = (editor, monaco) => {
    monacoRef.current = editor;

    const constrainedInstance = constrainedEditor(monaco);
    const model = editor.getModel();
    constrainedInstance.initializeIn(editor);
    const maxLines = model.getLineCount();
    restrictions.push({
      range: [1, 1, maxLines, 1],
      allowMultiline: true
    });

    constrainedInstance.addRestrictionsTo(model, restrictions);
  };

  const handleEditorChange = (value) => {
    setCode(value);
  };

  const handleSubmit = async () => {
    setOutput('');
    setFeedback('');
    setIsLoading(true);

    try {
      const response = await fetch(`${apiUrl}/submit_agent`, {
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
      } else if (data.status === "error") {
        toast.error(data.message, { position: "top-center" });
        setIsLoading(false);
      } else if (data.detail) {
        toast.error(data.detail, { position: "top-center" });
        setIsLoading(false);
      }
    } catch (error) {
      console.error('Error:', error);
      setIsLoading(false);
    }
  };

  return (
    <div>
      <div className="team-info-container">
      {currentUser.name && <h1 className="team-id">TEAM: {currentUser.name}</h1>}
      {currentLeague.game &&   <h1 className="team-game">GAME: {currentLeague.game}</h1>}
      {currentLeague.name &&   <h1 className="team-league">LEAGUE: {currentLeague.name}</h1>}
      </div>
      <div className="editor-container">
        <h1>AGENT GAMES CODE SUBMISSION</h1>
        <InstructionPopup instructions={instructionData} homescreen={false} />
        {code && 
          <Editor
            height="535px"
            width="880px"
            theme="vs-dark"
            defaultLanguage="python"
            defaultValue={code}
            onChange={handleEditorChange}
            onMount={handleEditorDidMount}
            options={editorOptions}
          />
        }
        <UserTooltip title="⚠️ INFO <br />Enter your code above and then submit to see results below." arrow disableFocusListener disableTouchListener>
          <button onClick={handleSubmit} className="submit-button" disabled={isLoading}>
            {isLoading ? 'Submitting...' : 'Submit Code'}
          </button>
        </UserTooltip>
        <div className="output-container">
          {output ? (
            <>
              <ResultsDisplay data={output} data_message={messageData} />
              {feedback && <MarkdownFeedback feedback={feedback} />}
            </>
          ) : (
            isLoading ? <p>Loading results...</p> : <p>Submit to see results</p>
          )}
        </div>
      </div>
    </div>
  );
}

export default AgentSubmission;