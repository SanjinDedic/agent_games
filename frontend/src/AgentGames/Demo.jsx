import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { toast } from 'react-toastify';
import moment from 'moment-timezone';
import { setToken } from '../slices/authSlice';
import { featuredGames } from './Feedback/games';

function Demo() {
    const navigate = useNavigate();
    const dispatch = useDispatch();
    const apiUrl = useSelector((state) => state.settings.agentApiUrl);
    const [isLoading, setIsLoading] = useState(false);
    const [username, setUsername] = useState('');
    const [email, setEmail] = useState('');
    const [errors, setErrors] = useState({});
    const [countdown, setCountdown] = useState('');
    const [contentOverview, setContentOverview] = useState(null);

    // What the demo includes (5 tutorials / 5 lessons) plus library totals
    useEffect(() => {
        let cancelled = false;
        fetch(`${apiUrl}/demo/content_overview`)
            .then((response) => (response.ok ? response.json() : null))
            .then((data) => {
                if (!cancelled && data) setContentOverview(data);
            })
            .catch(() => {
                // Purely informational section — hide it if the fetch fails
            });
        return () => {
            cancelled = true;
        };
    }, [apiUrl]);

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

        // Team name validation (alphanumeric, max 10 chars)
        if (!username.trim()) {
            newErrors.username = 'Team name is required';
        } else if (username.length > 10) {
            newErrors.username = 'Team name must be 10 characters or less';
        } else if (!/^[a-zA-Z0-9]+$/.test(username)) {
            newErrors.username = 'Team name must be alphanumeric';
        }

        // Email validation (required)
        if (!email.trim()) {
            newErrors.email = 'Email address is required';
        } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
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
                    email: email.trim()
                })
            });

            const data = await response.json();

            if (response.ok) {
                dispatch(setToken(data.access_token));

                toast.success(`Demo started! You have ${data.expires_in_minutes} minutes to explore.`);
                navigate('/AgentLeagueSignUp');
            } else {
                toast.error(data.detail || 'Failed to start demo');
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
                                Agent Games is a platform where you can write algorithms to take on various strategic games.
                                Your agent will face other agents in coding challenges to see whose algorithm performs best.
                            </p>
                            <p className="text-ui mb-4">
                                With the demo mode, you can try out the platform for 60 minutes without creating an account.
                                You'll be able to:
                            </p>
                            <ul className="list-disc pl-6 space-y-2 text-ui">
                                <li>Code your own agent in Python</li>
                                <li>Submit your agent to test against our built-in agents</li>
                                <li>See the results of your agent's performance</li>
                                <li>Make changes and improve your strategy</li>
                            </ul>
                        </div>

                        <div className="bg-ui-lighter p-6 rounded-lg">
                            <h2 className="text-xl font-semibold text-ui-dark mb-4">Available Demo Games:</h2>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                {featuredGames.map((game) => (
                                    <div key={game.name} className="bg-white p-4 rounded shadow">
                                        <h3 className="font-medium text-lg">{game.displayName}</h3>
                                        <p className="text-sm text-ui">{game.shortDescription || game.description}</p>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {contentOverview && (
                            <div className="bg-ui-lighter p-6 rounded-lg">
                                <h2 className="text-xl font-semibold text-ui-dark mb-4">Included in the Demo:</h2>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div className="bg-white p-4 rounded shadow">
                                        <h3 className="font-medium text-lg mb-2">
                                            {contentOverview.demo_tutorials.length} Tutorials
                                            <span className="text-sm text-ui font-normal"> (of {contentOverview.total_tutorials} on the full platform)</span>
                                        </h3>
                                        <ul className="list-disc pl-5 space-y-1 text-sm text-ui">
                                            {contentOverview.demo_tutorials.map((title) => (
                                                <li key={title}>{title}</li>
                                            ))}
                                        </ul>
                                    </div>
                                    <div className="bg-white p-4 rounded shadow">
                                        <h3 className="font-medium text-lg mb-2">
                                            {contentOverview.demo_lessons.length} Lessons
                                            <span className="text-sm text-ui font-normal"> (of {contentOverview.total_lessons} on the full platform)</span>
                                        </h3>
                                        <ul className="list-disc pl-5 space-y-1 text-sm text-ui">
                                            {contentOverview.demo_lessons.map((title) => (
                                                <li key={title}>{title}</li>
                                            ))}
                                        </ul>
                                    </div>
                                </div>
                            </div>
                        )}

                        <div className="bg-white p-6 rounded-lg shadow">
                            <h2 className="text-xl font-semibold text-ui-dark mb-4">Get Started</h2>

                            <div className="space-y-4">
                                <div>
                                    <label className="block text-ui-dark mb-2">
                                        Team Name <span className="text-danger">*</span>
                                    </label>
                                    <input
                                        type="text"
                                        value={username}
                                        onChange={(e) => setUsername(e.target.value)}
                                        placeholder="Enter a team name (max 10 chars)"
                                        className={`w-full p-3 rounded-lg border ${errors.username ? 'border-danger' : 'border-ui-light'}`}
                                        maxLength={10}
                                    />
                                    {errors.username && <p className="text-danger mt-1 text-sm">{errors.username}</p>}
                                    <p className="text-ui text-sm mt-1">Alphanumeric characters only, 10 characters max.</p>
                                </div>

                                <div>
                                    <label className="block text-ui-dark mb-2">
                                        Email <span className="text-danger">*</span>
                                    </label>
                                    <input
                                        type="email"
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        placeholder="Enter your email"
                                        className={`w-full p-3 rounded-lg border ${errors.email ? 'border-danger' : 'border-ui-light'}`}
                                        required
                                    />
                                    {errors.email && <p className="text-danger mt-1 text-sm">{errors.email}</p>}
                                    <p className="text-ui text-sm mt-1">A valid email address is required to start the demo.</p>
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