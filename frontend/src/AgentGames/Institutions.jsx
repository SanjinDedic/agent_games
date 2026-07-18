import React, { useState } from 'react';
import { Link } from 'react-router-dom';

const apiUrl = import.meta.env.VITE_AGENT_API_URL;

// One-time 90-day pass is the default, stressed offer. The annual auto-renewing
// subscription (higher price) is tucked into a collapsible section per tier.
const TIERS = [
    {
        id: 'club',
        name: 'Club & School',
        teams: 'Up to 100 student teams',
        oncePrice: 99,
        yearPrice: 299,
        features: [
            'Up to 100 student teams',
            'All games and coding challenges',
            'Leagues and leaderboards',
            'In-browser Python editor',
        ],
    },
    {
        id: 'university',
        name: 'University & Large Cohort',
        teams: 'Up to 500 teams / students',
        oncePrice: 299,
        yearPrice: 599,
        features: [
            'Up to 500 teams / students',
            'All games and coding challenges',
            'Leagues and leaderboards',
            'In-browser Python editor',
        ],
    },
];

function Institutions() {
    // Loading key is `${tier}:${autoRenew}` so each button tracks its own state.
    const [loadingKey, setLoadingKey] = useState(null);
    const [expanded, setExpanded] = useState({ club: false, university: false });

    const handleCheckout = async (tier, autoRenew) => {
        const key = `${tier}:${autoRenew}`;
        setLoadingKey(key);
        try {
            const res = await fetch(`${apiUrl}/payments/create-checkout-session`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tier, auto_renew: autoRenew }),
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
            setLoadingKey(null);
        }
    };

    const toggleExpanded = (tier) =>
        setExpanded((s) => ({ ...s, [tier]: !s[tier] }));

    return (
        <div className="min-h-screen pt-16 bg-ui-lighter">
            <div className="w-full max-w-5xl mx-auto px-4 py-12">
                {/* Intro */}
                <div className="text-center mb-12">
                    <h1 className="text-3xl md:text-4xl font-bold text-ui-dark mb-4">
                        Agent Games for Institutions
                    </h1>
                    <p className="text-lg text-ui max-w-3xl mx-auto">
                        Agent Games is an educational platform where students write
                        Python algorithms and put them to the test against other
                        agents in structured coding challenges and leagues. It is
                        built for <span className="font-semibold">high schools</span>,{' '}
                        <span className="font-semibold">universities</span>, and{' '}
                        <span className="font-semibold">coding clubs</span> that want a
                        hands-on, engaging way to teach programming, algorithmic
                        thinking, and computational concepts.
                    </p>
                </div>

                {/* Pricing */}
                <div className="mb-12">
                    <h2 className="text-2xl font-bold text-ui-dark text-center mb-2">
                        Pricing
                    </h2>
                    <p className="text-center text-ui mb-8 max-w-3xl mx-auto">
                        Start with a one-off <span className="font-semibold">90-day pass</span> —
                        no subscription, no auto-renewal. All prices in AUD. Need
                        ongoing access? An annual auto-renewing plan is available too.
                        Just one class?{' '}
                        <Link to="/Teachers" className="text-primary font-semibold underline">
                            See teacher plans
                        </Link>{' '}
                        — from $29.
                    </p>
                    <div className="grid gap-6 md:grid-cols-2 items-start">
                        {TIERS.map((tier) => {
                            const onceKey = `${tier.id}:false`;
                            const yearKey = `${tier.id}:true`;
                            const isExpanded = expanded[tier.id];
                            return (
                                <div
                                    key={tier.id}
                                    className="bg-white rounded-lg shadow-lg p-8 border-2 border-primary flex flex-col"
                                >
                                    <h3 className="text-xl font-semibold text-ui-dark mb-2">
                                        {tier.name}
                                    </h3>
                                    <p className="text-ui mb-4">{tier.teams}</p>

                                    {/* Stressed 90-day one-off offer */}
                                    <span className="inline-block self-start text-xs font-semibold uppercase tracking-wide bg-primary/10 text-primary px-2 py-1 rounded mb-2">
                                        Best to start
                                    </span>
                                    <div className="mb-1">
                                        <span className="text-4xl font-bold text-primary">
                                            ${tier.oncePrice}
                                        </span>
                                        <span className="text-ui"> AUD</span>
                                    </div>
                                    <p className="text-sm text-ui mb-6">
                                        One-off payment · 90 days of full access · no auto-renewal
                                    </p>

                                    <ul className="text-ui space-y-2 mb-6 list-disc pl-5">
                                        {tier.features.map((f) => (
                                            <li key={f}>{f}</li>
                                        ))}
                                    </ul>

                                    <button
                                        onClick={() => handleCheckout(tier.id, false)}
                                        disabled={loadingKey !== null}
                                        className="w-full bg-primary hover:bg-primary-hover text-white py-3 px-6 rounded font-semibold disabled:opacity-60"
                                    >
                                        {loadingKey === onceKey
                                            ? 'Redirecting…'
                                            : `Buy 90 days — $${tier.oncePrice}`}
                                    </button>

                                    {/* Collapsible annual auto-renew option */}
                                    <div className="mt-4 border-t border-ui-light pt-4">
                                        <button
                                            type="button"
                                            onClick={() => toggleExpanded(tier.id)}
                                            aria-expanded={isExpanded}
                                            className="w-full flex items-center justify-between text-sm font-medium text-ui hover:text-ui-dark"
                                        >
                                            <span>
                                                Prefer ongoing access? See annual plans
                                            </span>
                                            <span
                                                className={`transform transition-transform ${
                                                    isExpanded ? 'rotate-180' : ''
                                                }`}
                                            >
                                                ▾
                                            </span>
                                        </button>

                                        {isExpanded && (
                                            <div className="mt-4">
                                                <div className="mb-1">
                                                    <span className="text-2xl font-bold text-ui-dark">
                                                        ${tier.yearPrice}
                                                    </span>
                                                    <span className="text-ui"> AUD / year</span>
                                                </div>

                                                {/* Option 2 — annual subscription, card */}
                                                <p className="text-sm text-ui mt-3 mb-2">
                                                    Annual subscription · pay by card ·
                                                    auto-renews every year · cancel anytime
                                                </p>
                                                <button
                                                    onClick={() =>
                                                        handleCheckout(tier.id, true)
                                                    }
                                                    disabled={loadingKey !== null}
                                                    className="w-full bg-white border-2 border-primary text-primary hover:bg-ui-lighter py-2 px-6 rounded font-semibold disabled:opacity-60"
                                                >
                                                    {loadingKey === yearKey
                                                        ? 'Redirecting…'
                                                        : `Subscribe by card — $${tier.yearPrice}/yr`}
                                                </button>

                                                {/* Option 3 — annual subscription, invoiced */}
                                                <p className="text-sm text-ui mt-5 mb-2">
                                                    Annual subscription · invoiced to your
                                                    institution (net 30) · access on issue
                                                </p>
                                                <Link
                                                    to={`/InstitutionInvoiceSignup?tier=${tier.id}`}
                                                    className="block w-full text-center bg-white border border-ui-light text-ui-dark hover:bg-ui-lighter py-2 px-6 rounded font-semibold"
                                                >
                                                    Get invoiced — ${tier.yearPrice}/yr
                                                </Link>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>

                {/* Open source support */}
                <div className="bg-league-blue text-white rounded-lg shadow-lg p-8 mb-12 text-center">
                    <h2 className="text-2xl font-bold mb-3">
                        Support open source education
                    </h2>
                    <p className="text-league-text max-w-3xl mx-auto mb-6">
                        Agent Games is open source. By subscribing, your institution
                        directly supports the ongoing development of the platform —
                        new games, features, and improvements that stay free and open
                        for the whole community.
                    </p>
                    <a
                        href="https://github.com/SanjinDedic/agent_games"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-block bg-white text-league-blue hover:bg-league-text py-2 px-6 rounded font-semibold"
                    >
                        View the project on GitHub
                    </a>
                </div>

                {/* Signup placeholder */}
                <div className="bg-white rounded-lg shadow-lg p-8 text-center">
                    <h2 className="text-2xl font-bold text-ui-dark mb-3">
                        Institution Signup
                    </h2>
                    <p className="text-ui mb-4">
                        Choose a plan above and pay to get started — after payment you
                        are taken straight to signup to set up your institution. Need
                        help or have a pricing question? Get in touch.
                    </p>
                    <a
                        href="mailto:ozrobotix@gmail.com?subject=Agent%20Games%20Institution%20Signup"
                        className="inline-block bg-primary hover:bg-primary-hover text-white py-2 px-6 rounded font-semibold"
                    >
                        Contact us to get started
                    </a>
                </div>
            </div>
        </div>
    );
}

export default Institutions;
