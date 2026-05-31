import React from 'react';

function Institutions() {
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
                    <p className="text-center text-ui mb-8">
                        Annual subscription. All prices in AUD.
                    </p>
                    <div className="grid gap-6 md:grid-cols-2">
                        {/* Tier 1 */}
                        <div className="bg-white rounded-lg shadow-lg p-8 border border-ui-light flex flex-col">
                            <h3 className="text-xl font-semibold text-ui-dark mb-2">
                                Club &amp; School
                            </h3>
                            <p className="text-ui mb-4">Up to 100 student teams</p>
                            <div className="mb-6">
                                <span className="text-4xl font-bold text-primary">
                                    $299
                                </span>
                                <span className="text-ui"> AUD / year</span>
                            </div>
                            <ul className="text-ui space-y-2 mb-6 list-disc pl-5">
                                <li>Up to 100 student teams</li>
                                <li>All games and coding challenges</li>
                                <li>Leagues and leaderboards</li>
                                <li>In-browser Python editor</li>
                            </ul>
                        </div>
                        {/* Tier 2 */}
                        <div className="bg-white rounded-lg shadow-lg p-8 border-2 border-primary flex flex-col">
                            <h3 className="text-xl font-semibold text-ui-dark mb-2">
                                University &amp; Large Cohort
                            </h3>
                            <p className="text-ui mb-4">Up to 1000 student teams</p>
                            <div className="mb-6">
                                <span className="text-4xl font-bold text-primary">
                                    $599
                                </span>
                                <span className="text-ui"> AUD / year</span>
                            </div>
                            <ul className="text-ui space-y-2 mb-6 list-disc pl-5">
                                <li>Up to 1000 student teams</li>
                                <li>All games and coding challenges</li>
                                <li>Leagues and leaderboards</li>
                                <li>In-browser Python editor</li>
                            </ul>
                        </div>
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
                        Online signup is coming soon. To register your institution or
                        ask about pricing, get in touch and we will set you up.
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
