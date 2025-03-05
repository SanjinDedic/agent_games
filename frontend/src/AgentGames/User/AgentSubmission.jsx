// Main component: AgentSubmission.jsx
import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { toast } from 'react-toastify';
import { checkTokenExpiry } from '../../slices/authSlice';
import CodeEditor from './CodeEditor';
import StatusBar from './StatusBar';
import FeedbackDisplay from './FeedbackDisplay';
import ControlPanel from './ControlPanel';

function AgentSubmission() {
    // State management
    const [code, setCode] = useState('');
    const [starterCode, setStarterCode] = useState('');
    const [lastSubmission, setLastSubmission] = useState('');
    const [output, setOutput] = useState('');
    const [feedback, setFeedback] = useState('');
    const [instructionData, setInstructionData] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [hasLastSubmission, setHasLastSubmission] = useState(false);
    const [shouldCollapseInstructions, setShouldCollapseInstructions] = useState(false);
    const editorRef = useRef(null);

    // Redux hooks
    const dispatch = useDispatch();
    const navigate = useNavigate();
    const apiUrl = useSelector((state) => state.settings.agentApiUrl);
    const currentLeague = useSelector((state) => state.leagues.currentLeague);
    const accessToken = useSelector((state) => state.auth.token);
    const currentUser = useSelector((state) => state.auth.currentUser);
    const isAuthenticated = useSelector((state) => state.auth.isAuthenticated);

    // Check authentication on component mount
    useEffect(() => {
        const tokenExpired = dispatch(checkTokenExpiry());
        if (!isAuthenticated || currentUser.role !== "student" || tokenExpired) {
            navigate('/AgentLogin');
        } else {
            loadLatestSubmission();
            if (currentLeague && currentLeague.game) {
                loadInstructions();
            }
        }
    }, [navigate, currentLeague]);

    // Load the latest code submission
    const loadLatestSubmission = async () => {
        try {
            const response = await fetch(`${apiUrl}/user/get-team-submission`, {
                headers: { 'Authorization': `Bearer ${accessToken}` }
            });
            const data = await response.json();

            if (data.status === "success" && data.data && data.data.code) {
                setLastSubmission(data.data.code);
                setCode(data.data.code);
                setHasLastSubmission(true);
            } else {
                setHasLastSubmission(false);
            }
        } catch (error) {
            console.error('Error loading submission:', error);
            setHasLastSubmission(false);
        }
    };

    // Load game instructions and starter code
    const loadInstructions = async () => {
        if (!currentLeague || !currentLeague.game) return;

        try {
            const response = await fetch(`${apiUrl}/user/get-game-instructions`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ game_name: currentLeague.game }),
            });

            const data = await response.json();

            if (data.status === "success" && data.data) {
                if (data.data.starter_code) {
                    let code_sample = data.data.starter_code;
                    if (code_sample.startsWith('\n')) {
                        code_sample = code_sample.slice(1);
                    }
                    setStarterCode(code_sample);
                    if (!hasLastSubmission) {
                        setCode(code_sample);
                    }
                }

                if (data.data.game_instructions) {
                    setInstructionData(data.data.game_instructions);
                }
            }
        } catch (error) {
            console.error('Error fetching game instructions:', error);
        }
    };

    // Submit code to the API
    const handleSubmit = async () => {
        if (!code || code.trim() === '') {
            toast.error('Please enter some code before submitting');
            return;
        }

        setOutput('');
        setFeedback('');
        setIsLoading(true);
        setShouldCollapseInstructions(true);

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
                setOutput(data.data.results);
                setFeedback(data.data.feedback);
                loadLatestSubmission();
            } else if (data.status === "error") {
                toast.error(data.message);
            }
        } catch (error) {
            console.error('Error during submission:', error);
            toast.error('Network error during submission. Please try again.');
        } finally {
            setIsLoading(false);
        }
    };

    // Load last submitted code
    const handleLoadLastSubmission = () => {
        if (hasLastSubmission && editorRef.current) {
            editorRef.current.setValue(lastSubmission);
            setCode(lastSubmission);
            toast.success('Loaded last submission');
        } else {
            toast.error('No previous submission found');
        }
    };

    // Reset code to starter template
    const handleReset = () => {
        if (starterCode && editorRef.current) {
            editorRef.current.setValue(starterCode);
            setCode(starterCode);
            toast.success('Code reset to starter template');
        } else {
            toast.error('Starter code template not available');
            loadInstructions();
        }
    };

    // Update editor reference when mounted
    const handleEditorDidMount = (editor) => {
        editorRef.current = editor;
    };

    return (
        <div className="min-h-screen pt-12 flex flex-col bg bg-white">
            <div className="flex flex-1 overflow-hidden">
                {/* Left side - Code Editor */}
                <div className="w-1/2 h-[calc(100vh-64px)] border-r border-[#1e1e1e] border-t-0 bg-[#1e1e1e] -mt-[1px]">
                    <CodeEditor
                        code={code}
                        onCodeChange={setCode}
                        onMount={handleEditorDidMount}
                    />
                </div>

                {/* Right side - Status, Feedback, and Controls */}
                <div className="w-1/2 flex flex-col h-[calc(100vh-64px)]">
                    {/* Status Bar */}
                    <StatusBar
                        team={currentUser.name}
                        game={currentLeague?.game}
                        league={currentLeague?.name}
                        isDemo={currentUser.is_demo}
                    />

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

                    {/* Control Panel */}
                    <ControlPanel
                        onSubmit={handleSubmit}
                        onLoadLast={handleLoadLastSubmission}
                        onReset={handleReset}
                        isLoading={isLoading}
                        hasLastSubmission={hasLastSubmission}
                        hasStarterCode={!!starterCode}
                    />
                </div>
            </div>
        </div>
    );
}

export default AgentSubmission;