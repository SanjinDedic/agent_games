import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { toast } from 'react-toastify';
import moment from 'moment-timezone';
import { login } from '../slices/authSlice';

function Demo() {
    const navigate = useNavigate();
    const dispatch = useDispatch();
    const apiUrl = useSelector((state) => state.settings.agentApiUrl);
    const [isLoading, setIsLoading] = useState(false);
    const [username, setUsername] = useState('');
    const [email, setEmail] = useState('');
    const [errors, setErrors] = useState({});
    const [countdown, setCountdown] = useState('');

    // Timer for countdown display if we have a demo session
    useEffect(() => {
        let timer;
        if (countdown) {
            timer = setInterval(() => {
                const expiryTime = moment(countdown);
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
    }, [countdown, navigate]);

    const validateInputs = () => {
        const newErrors = {};

        // Username validation (alphanumeric, max 10 chars)
        if (!username.trim()) {
            newErrors.username = 'Username is required';
        } else if (username.length > 10) {
            newErrors.username = 'Username must be 10 characters or less';
        } else if (!/^[a-zA-Z0-9]+$/.test(username)) {
            newErrors.username = 'Username must be alphanumeric';
        }

        // Email validation (optional)
        if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
            newErrors.email = 'Please enter a valid email address';
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleLaunchDemo = async () => {
        if (!validateInputs()) {
            return;
        }

        setIsLoading(true);
        try {
            const response = await fetch(`${apiUrl}/demo/launch_demo`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    username: username,
                    email: email || null
                })
            });

            const data = await response.json();

            if (data.status === 'success') {
                // Store demo user data
                const demoData = data.data;

                // Login with temporary demo credentials
                dispatch(login({
                    token: demoData.access_token,
                    name: demoData.username,
                    role: 'student',
                    is_demo: true,
                    exp: moment(demoData.expires_at).unix()
                }));

                toast.success(`Demo started! You have ${demoData.expires_in_minutes} minutes to explore.`);
                navigate('/AgentLeagueSignUp');
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
                                    <h3 className="font-medium text-lg">Lineup4</h3>
                                    <p className="text-sm text-ui">The strategic game of connecting four pieces in a row.</p>
                                </div>
                            </div>
                        </div>

                        <div className="bg-white p-6 rounded-lg shadow">
                            <h2 className="text-xl font-semibold text-ui-dark mb-4">Get Started</h2>

                            <div className="space-y-4">
                                <div>
                                    <label className="block text-ui-dark mb-2">
                                        Username <span className="text-danger">*</span>
                                    </label>
                                    <input
                                        type="text"
                                        value={username}
                                        onChange={(e) => setUsername(e.target.value)}
                                        placeholder="Enter a username (max 10 chars)"
                                        className={`w-full p-3 rounded-lg border ${errors.username ? 'border-danger' : 'border-ui-light'}`}
                                        maxLength={10}
                                    />
                                    {errors.username && <p className="text-danger mt-1 text-sm">{errors.username}</p>}
                                    <p className="text-ui text-sm mt-1">Alphanumeric characters only, 10 characters max.</p>
                                </div>

                                <div>
                                    <label className="block text-ui-dark mb-2">
                                        Email <span className="text-ui text-sm">(Optional)</span>
                                    </label>
                                    <input
                                        type="email"
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        placeholder="Enter your email (optional)"
                                        className={`w-full p-3 rounded-lg border ${errors.email ? 'border-danger' : 'border-ui-light'}`}
                                    />
                                    {errors.email && <p className="text-danger mt-1 text-sm">{errors.email}</p>}
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
        </div>
    );
}

export default Demo;