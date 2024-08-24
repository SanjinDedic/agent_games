import React, { useState, useEffect, useRef } from 'react';
import Editor from "@monaco-editor/react";
import { constrainedEditor } from "constrained-editor-plugin";
import ResultsDisplay from '../Utilities/ResultsDisplay';
import { toast } from 'react-toastify';
import { useNavigate } from 'react-router-dom';
import './css/submission.css'
import UserTooltip from '../Utilities/UserTooltips';
import InstructionPopup from '../Utilities/InstructionPopup';
import { useDispatch, useSelector } from 'react-redux';
import { logout } from '../../slices/authSlice';
import { clearLeagues } from '../../slices/leaguesSlice';
import { clearTeam } from '../../slices/teamsSlice';

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
  const [instructionData, setInstructionData] = useState('');
  const [messageData, setmessageData] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const restrictions = [];
  const navigate = useNavigate();


  useEffect(() => {
    handleInstructions();
    if (!isAuthenticated || currentUser.role !== "student") {
      // Redirect to the home page if not authenticated
      navigate('/AgentLogin');
    }
  }, [navigate]);


  const handleInstructions = async () => {
    
    fetch(`${apiUrl}/get_game_instructions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ game_name: currentLeague.game }),
    })
      .then(response => response.json())
      .then(data => {
        if (data.status === "success") {
          let code_sample = data.data.starter_code;
          code_sample = code_sample.slice(1);
          setCode(code_sample);
          setInstructionData(data.data.game_instructions);
        } else if (data.status === "error") {
          toast.error(data.message, {
            position: "top-center"
          });
        } else if (data.detail) {
          toast.error(data.detail, {
            position: "top-center"
          });
          
        }

      })
      .catch(error => console.error('Error:', error), setIsLoading(false));
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
    setOutput(''); // Reset output on new submission
    setIsLoading(true);
    
    fetch(`${apiUrl}/submit_agent`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      },
      body: JSON.stringify({ code: code }),
    })
      .then(response => response.json())
      .then(data => {
        if (data.status === "success") {
          setIsLoading(false);
          setOutput(data.data.results);
          setmessageData(data.message);
        } else if (data.status === "error") {
          toast.error(data.message, {
            position: "top-center"
          });
        } else if (data.detail) {
          toast.error(data.detail, {
            position: "top-center"
          });
          
        }

      })
      .catch(error => console.error('Error:', error), setIsLoading(false));
  };


  return (
    <div>
      <div className="team-info-container">
        <h1 className="team-id">TEAM: {currentUser.name}</h1>
        <h1 className="team-game">GAME: {currentLeague.game}</h1>
        <h1 className="team-league">LEAGUE: {currentLeague.name}</h1>
      </div>
      <div className="editor-container">

        <h1>AGENT GAMES CODE SUBMISSION</h1>
        <InstructionPopup  instructions={instructionData} homescreen={false}/>
        {code && 
         <Editor
          height="535px" // By default, it does not have a size. You need to set it.
          width="800px"
          theme="vs-dark"
          defaultLanguage="python"
          defaultValue={code}
          onChange={handleEditorChange}
          onMount={handleEditorDidMount}
        /> }
        <UserTooltip title={"⚠️ INFO <br />Enter your code above and then submit to see results below."} arrow disableFocusListener disableTouchListener>
        <button onClick={handleSubmit} className="submit-button" disabled={isLoading}>{isLoading ? 'Submitting...' : 'Submit Code'}</button>
        </UserTooltip>
        <div className="output-container">
          {output ? (<ResultsDisplay data={output} data_message={messageData} />) : (
            isLoading ? <p>Loading results...</p> : <p>Submit to see results</p>)}
        </div>
      </div>
    </div>
  );
}

export default AgentSubmission;