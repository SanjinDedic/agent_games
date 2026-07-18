import React, { useState } from 'react';
import { Link } from 'react-router-dom';

const apiUrl = import.meta.env.VITE_AGENT_API_URL;

// Teacher plans are one-off 90-day passes only (no annual/invoice options).
// Both tiers create a teacher account: classroom/student wording, same
// capabilities as an institution. "school" bills the same Stripe Price as the
// university 90-day pass — the backend maps the tier.
const PLANS = [
    {
        id: 'teacher',
        name: 'Teacher',
        students: 'Up to 26 students',
        price: 29,
        highlight: 'Perfect for one class',
        features: [
            'Up to 26 students',
            'Classrooms with leaderboards',
            'All games and coding challenges',
            'In-browser Python editor',
        ],
    },
    {
        id: 'school',
        name: 'Whole School',
        students: 'Up to 500 students',
        price: 299,
        highlight: 'Every class, one account',
        features: [
            'Up to 500 students',
            'Unlimited classrooms and leaderboards',
            'All games and coding challenges',
            'In-browser Python editor',
        ],
    },
];

function Teachers() {
    const [loadingTier, setLoadingTier] = useState(null);

    const handleCheckout = async (tier) => {
        setLoadingTier(tier);
        try {
            const res = await fetch(`${apiUrl}/payments/create-checkout-session`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tier, auto_renew: false }),
            });
            const json = await res.json();
            if (res.ok && json?.url) {
                window.location.href = json.url;
                return;
            }
            alert('Could not start checkout. Please try again.');
        } catch (err) {
            alert('Could not start checkout. Please try again.');
        } finally {
            setLoadingTier(null);
        }
    };

    return (
        <div className="min-h-screen pt-16 bg-ui-lighter">
            <div className="w-full max-w-5xl mx-auto px-4 py-12">
                {/* Intro */}
                <div className="text-center mb-12">
                    <h1 className="text-3xl md:text-4xl font-bold text-ui-dark mb-4">
                        Agent Games for Teachers
                    </h1>
                    <p className="text-lg text-ui max-w-3xl mx-auto">
                        Set up a classroom in minutes: your students write Python
                        agents in the browser and compete on live leaderboards.
                        Structured coding challenges teach programming, algorithmic
                        thinking, and computational concepts — no installs, no setup.
                    </p>
                    <p className="text-ui mt-4">
                        Already have an account?{' '}
                        <Link to="/Teacher" className="text-primary font-semibold underline">
                            Teacher login
                        </Link>
                    </p>
                </div>

                {/* Pricing */}
                <div className="mb-12">
                    <h2 className="text-2xl font-bold text-ui-dark text-center mb-2">
                        Pricing
                    </h2>
                    <p className="text-center text-ui mb-8 max-w-3xl mx-auto">
                        One-off <span className="font-semibold">90-day pass</span> — no
                        subscription, no auto-renewal. All prices in AUD.
                    </p>
                    <div className="grid gap-6 md:grid-cols-2 items-start">
                        {PLANS.map((plan) => (
                            <div
                                key={plan.id}
                                className="bg-white rounded-lg shadow-lg p-8 border-2 border-primary flex flex-col"
                            >
                                <h3 className="text-xl font-semibold text-ui-dark mb-2">
                                    {plan.name}
                                </h3>
                                <p className="text-ui mb-4">{plan.students}</p>

                                <span className="inline-block self-start text-xs font-semibold uppercase tracking-wide bg-primary/10 text-primary px-2 py-1 rounded mb-2">
                                    {plan.highlight}
                                </span>
                                <div className="mb-1">
                                    <span className="text-4xl font-bold text-primary">
                                        ${plan.price}
                                    </span>
                                    <span className="text-ui"> AUD</span>
                                </div>
                                <p className="text-sm text-ui mb-6">
                                    One-off payment · 90 days of full access · no auto-renewal
                                </p>

                                <ul className="text-ui space-y-2 mb-6 list-disc pl-5">
                                    {plan.features.map((f) => (
                                        <li key={f}>{f}</li>
                                    ))}
                                </ul>

                                <button
                                    onClick={() => handleCheckout(plan.id)}
                                    disabled={loadingTier !== null}
                                    className="w-full bg-primary hover:bg-primary-hover text-white py-3 px-6 rounded font-semibold disabled:opacity-60"
                                >
                                    {loadingTier === plan.id
                                        ? 'Redirecting…'
                                        : `Buy 90 days — $${plan.price}`}
                                </button>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Institution pointer */}
                <div className="bg-white rounded-lg shadow-lg p-8 text-center">
                    <h2 className="text-2xl font-bold text-ui-dark mb-3">
                        Buying for an institution?
                    </h2>
                    <p className="text-ui mb-4">
                        Universities, coding clubs, and schools that prefer team-based
                        leagues (or need annual/invoiced billing) can use the
                        institution plans instead.
                    </p>
                    <Link
                        to="/Institutions"
                        className="inline-block bg-primary hover:bg-primary-hover text-white py-2 px-6 rounded font-semibold"
                    >
                        See institution plans
                    </Link>
                </div>
            </div>
        </div>
    );
}

export default Teachers;
