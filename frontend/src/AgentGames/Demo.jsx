import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { toast } from 'react-toastify';
import moment from 'moment-timezone';
import { login } from '../slices/authSlice';
import Modal from '@mui/material/Modal';
import Box from '@mui/material/Box';
import { setCurrentLeague } from '../slices/leaguesSlice'; // Add this import

function Demo() {
    const navigate = useNavigate();
    const dispatch = useDispatch();
    const apiUrl = useSelector((state) => state.settings.agentApiUrl);
    const [isLoading, setIsLoading] = useState(false);
    const [modalOpen, setModalOpen] = useState(false);
    const [demoData, setDemoData] = useState(null);
    const [countdown, setCountdown] = useState('');
    const [availableGames, setAvailableGames] = useState([]);
    const [selectedGame, setSelectedGame] = useState('');

    // Timer for countdown display
    useEffect(() => {
        let timer;
        if (demoData && demoData.expires_at) {
            timer = setInterval(() => {
                const expiryTime = moment(demoData.expires_at);
                const now = moment();
                const diff = expiryTime.diff(now);

                if (diff <= 0) {
                    clearInterval(timer);
                    setCountdown('Expired');
                    toast.error('Demo session has expired');
                    navigate('/');
                    return;
                }

                const duration = moment.duration(diff);
                const minutes = Math.floor(duration.asMinutes());
                const seconds = Math.floor(duration.seconds());
                setCountdown(`${minutes}:${seconds < 10 ? '0' : ''}${seconds}`);
            }, 1000);
        }

        return () => {
            if (timer) clearInterval(timer);
        };
    }, [demoData, navigate]);

    const handleLaunchDemo = async () => {
        setIsLoading(true);
        try {
            const response = await fetch(`${apiUrl}/demo/launch_demo`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            const data = await response.json();

            if (data.status === 'success') {
                // Store demo user data
                setDemoData(data.data);
                setAvailableGames(data.data.available_games || []);
                if (data.data.available_games?.length > 0) {
                    setSelectedGame(data.data.available_games[0]);
                }

                // Login with temporary demo credentials
                dispatch(login({
                    token: data.data.access_token,
                    name: data.data.username,
                    role: 'student',
                    is_demo: true,
                    exp: moment(data.data.expires_at).unix()
                }));

                // Show modal with game selection
                setModalOpen(true);
            } else {
                toast.error(data.message || 'Failed to start demo');
            }
        } catch (error) {
            console.error('Error launching demo:', error);
            toast.error('Network error while starting demo');
        } finally {
            setIsLoading(false);
        }
    };

    const handleGameSelect = async () => {
        if (!selectedGame) {
            toast.error('Please select a game to play');
            return;
        }

        try {
            const response = await fetch(`${apiUrl}/demo/select_game`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${demoData.access_token}`
                },
                body: JSON.stringify({
                    game_name: selectedGame
                })
            });

            const data = await response.json();

            if (data.status === 'success') {
                // IMPORTANT: Save the league information to Redux before navigating
                // This ensures the submission page knows which league is selected
                dispatch(setCurrentLeague({
                    name: data.data.league_name,
                    game: data.data.game,
                    id: data.data.league_id
                }));

                // Close modal and redirect to submission page
                setModalOpen(false);
                toast.success(`Starting demo with ${selectedGame}!`);

                // Short delay to ensure Redux state is updated
                setTimeout(() => {
                    navigate('/AgentSubmission');
                }, 100);
            } else {
                toast.error(data.message || 'Failed to select game');
            }
        } catch (error) {
            console.error('Error selecting game:', error);
            toast.error('Network error while selecting game');
        }
    };

    const handleCloseModal = () => {
        setModalOpen(false);
        // Navigate back to home if user cancels
        navigate('/');
    };

    return (
        <div className="min-h-screen pt-16 flex flex-col items-center justify-center bg-ui-lighter">
            <div className="w-full max-w-4xl px-4">
                <div className="bg-white rounded-lg shadow-lg p-8">
                    <h1 className="text-3xl font-bold text-ui-dark mb-6">Try Agent Games Without an Account</h1>

                    <div className="space-y-6">
                        <div className="bg-ui-lighter p-6 rounded-lg">
                            <h2 className="text-xl font-semibold text-ui-dark mb-4">What is Agent Games?</h2>
                            <p className="text-ui mb-4">
                                Agent Games is a platform where you can write algorithms to compete in various strategic games.
                                Your agent will face other agents in competitions to see whose algorithm performs best.
                            </p>
                            <p className="text-ui mb-4">
                                With the demo mode, you can try out the platform for 60 minutes without creating an account.
                                You'll be able to:
                            </p>
                            <ul className="list-disc pl-6 space-y-2 text-ui">
                                <li>Code your own agent in Python</li>
                                <li>Submit your agent to compete against our built-in agents</li>
                                <li>See the results of your agent's performance</li>
                                <li>Make changes and improve your strategy</li>
                            </ul>
                        </div>

                        <div className="bg-ui-lighter p-6 rounded-lg">
                            <h2 className="text-xl font-semibold text-ui-dark mb-4">Available Demo Games:</h2>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                <div className="bg-white p-4 rounded shadow">
                                    <h3 className="font-medium text-lg">Greedy Pig</h3>
                                    <p className="text-sm text-ui">A risk/reward dice game. When do you bank your points?</p>
                                </div>
                                <div className="bg-white p-4 rounded shadow">
                                    <h3 className="font-medium text-lg">Prisoner's Dilemma</h3>
                                    <p className="text-sm text-ui">The classic cooperation vs. betrayal game theory problem.</p>
                                </div>
                                <div className="bg-white p-4 rounded shadow">
                                    <h3 className="font-medium text-lg">Connect4</h3>
                                    <p className="text-sm text-ui">The strategic game of connecting four pieces in a row.</p>
                                </div>
                            </div>
                        </div>

                        <div className="flex justify-center">
                            <button
                                onClick={handleLaunchDemo}
                                disabled={isLoading}
                                className="py-3 px-8 text-xl font-medium text-white bg-primary hover:bg-primary-hover rounded-lg transition-colors duration-200 shadow-md disabled:bg-ui-light disabled:cursor-not-allowed"
                            >
                                {isLoading ? 'Starting Demo...' : 'Launch Demo Now'}
                            </button>
                        </div>

                        <div className="text-center text-sm text-ui">
                            <p>Demo access lasts for 60 minutes. No account required.</p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Game Selection Modal */}
            <Modal
                open={modalOpen}
                onClose={handleCloseModal}
                aria-labelledby="game-selection-modal"
            >
                <Box className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-white rounded-lg shadow-lg p-6 w-96">
                    <h2 className="text-xl font-bold text-ui-dark mb-4">Choose a Game to Play</h2>

                    <div className="mb-6">
                        <p className="text-ui mb-2">
                            Your demo session will expire in: <span className="font-bold text-primary">{countdown}</span>
                        </p>
                        <p className="text-sm text-ui">
                            You'll be able to submit agents and see their performance for the next hour.
                        </p>
                    </div>

                    <div className="mb-6">
                        <label className="block text-ui-dark mb-2">Select Game:</label>
                        <select
                            value={selectedGame}
                            onChange={(e) => setSelectedGame(e.target.value)}
                            className="w-full p-3 border border-ui-light rounded-lg bg-white text-ui-dark"
                        >
                            {availableGames.map((game) => (
                                <option key={game} value={game}>
                                    {game}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div className="flex justify-between">
                        <button
                            onClick={handleCloseModal}
                            className="py-2 px-4 text-ui border border-ui-light rounded hover:bg-ui-lighter transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={handleGameSelect}
                            className="py-2 px-4 text-white bg-primary hover:bg-primary-hover rounded transition-colors"
                        >
                            Start Playing
                        </button>
                    </div>
                </Box>
            </Modal>
        </div>
    );
}

export default Demo;