import React from 'react';

import { imageUrl } from '../config/assets';
import { featuredGames } from './Feedback/games';

const Homepage = () => {
  return (
    <div className="min-h-screen bg-ui-lighter pt-12">
      {/* Hero Section */}
      <section className="bg-gradient-to-br from-league-blue to-primary py-20">
        <div className="container mx-auto px-6 text-center">
          <h1 className="text-4xl md:text-6xl font-bold text-white mb-6">
           Python Programming Gamified
          </h1>
          <p className="text-xl text-league-text max-w-3xl mx-auto mb-10">
            Open Source platform for programming python agents that compete in strategic games. Great for universities, computing clubs and Computer Science enthusiasts
          </p>
          <div className="flex flex-col md:flex-row justify-center gap-4">
            <a href="/Demo" className="inline-block">
              <button className="bg-success hover:bg-success-hover text-white shadow-lg text-xl py-3 px-8 rounded">
                Try Demo
              </button>
            </a>
            <a href="/AgentLogin" className="inline-block">
              <button className="bg-white text-primary hover:bg-league-text hover:text-primary-dark shadow-lg text-xl py-3 px-8 rounded">
                Team Login
              </button>
            </a>
            <a href="/Institutions" className="inline-block">
              <button className="bg-primary-light hover:bg-primary text-white shadow-lg text-xl py-3 px-8 rounded">
                Institution Signup
              </button>
            </a>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-16">
        <div className="container mx-auto px-6">
          <h2 className="text-3xl font-bold text-ui-dark text-center mb-12">
            Why Agent Games?
          </h2>
          <div className="grid md:grid-cols-3 gap-8">
            {/* Feature 1 */}
            <div className="bg-white p-6 rounded-lg shadow-md">
              <div className="w-14 h-14 rounded-full bg-primary-light flex items-center justify-center mb-4">
                <svg
                  className="w-8 h-8 text-primary"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                  />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-ui-dark mb-2">
                Learn to Design Algorithms
              </h3>
              <p className="text-ui">
                Program agents that make strategic decisions, developing
                algorithmic thinking and problem-solving skills. 
              </p>
            </div>

            {/* Feature 2 */}
            <div className="bg-white p-6 rounded-lg shadow-md">
              <div className="w-14 h-14 rounded-full bg-success-light flex items-center justify-center mb-4">
                <svg
                  className="w-8 h-8 text-success"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M3 7h6M3 12h4.5M3 17h6M13.5 17V7m0 0L11 9.5m2.5-2.5L16 9.5M19.5 7v10m0 0L17 14.5m2.5 2.5l2.5-2.5"
                  />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-ui-dark mb-2">
                Host a contest in 5 minutes!
              </h3>
              <p className="text-ui">
                Live leaderboards, constant iteration, drama and deep learning, more fun than anything else you can do in a computing course.
              </p>
            </div>

            {/* Feature 3 - New Easy or Free section */}
            <div className="bg-white p-6 rounded-lg shadow-md">
              <div className="w-14 h-14 rounded-full bg-notice-yellowBg flex items-center justify-center mb-4">
                <svg
                  className="w-8 h-8 text-notice-yellow"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-ui-dark mb-2">
                Easy or Free
              </h3>
              <p className="text-ui">
                The platform is open source - clone the GitHub repo and host it
                yourself, or sign up for an affordable, hassle-free institution
                account.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Games Section */}
      <section className="py-16 bg-white">
        <div className="container mx-auto px-6">
          <h2 className="text-3xl font-bold text-ui-dark text-center mb-12">
            Featured Games
          </h2>
          <div className="grid md:grid-cols-3 gap-8">
            {featuredGames.map((game) => (
              <div
                key={game.name}
                className="bg-ui-lighter p-6 rounded-lg shadow-md"
              >
                <div className="mb-4 rounded overflow-hidden">
                  <img
                    src={imageUrl(game.thumbnail)}
                    alt={`${game.displayName} game`}
                    className="w-full h-48 object-cover"
                  />
                </div>
                <h3 className="text-xl font-semibold text-ui-dark mb-2">
                  {game.displayName}
                </h3>
                <p className="text-ui mb-4">{game.description}</p>
                <a href={`/Demo?game=${game.name}`}>
                  <span className="text-primary font-medium hover:text-primary-hover">
                    Try it →
                  </span>
                </a>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* For Schools Section */}
      <section className="py-16 bg-league-blue text-white">
        <div className="container mx-auto px-6">
          <div className="max-w-4xl mx-auto">
            <h2 className="text-3xl font-bold mb-6 text-center">
              For Educational Institutions
            </h2>
            <p className="text-lg mb-8 text-league-text text-center">
              Agent Games provides a powerful platform for teaching programming,
              algorithmic thinking, and computational concepts in a competitive
              and engaging environment.
            </p>
            <div className="bg-white/10 p-6 rounded-lg backdrop-blur-sm">
              <h3 className="text-xl font-semibold mb-4">
                Benefits for Schools and Universities:
              </h3>
              <ul className="space-y-3 text-league-text">
                <li className="flex items-start">
                  <svg
                    className="w-5 h-5 text-success mt-0.5 mr-2 flex-shrink-0"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                  <span>
                    Ready-to-use platform with structured coding challenges and
                    leagues
                  </span>
                </li>
                <li className="flex items-start">
                  <svg
                    className="w-5 h-5 text-success mt-0.5 mr-2 flex-shrink-0"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                  <span>
                    Comprehensive dashboard for managing student teams and
                    viewing results
                  </span>
                </li>
                <li className="flex items-start">
                  <svg
                    className="w-5 h-5 text-success mt-0.5 mr-2 flex-shrink-0"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                  <span>
                    Automatic evaluation and feedback for student submissions
                  </span>
                </li>
                <li className="flex items-start">
                  <svg
                    className="w-5 h-5 text-success mt-0.5 mr-2 flex-shrink-0"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                  <span>
                    Self-hosted option available for schools with specific
                    requirements
                  </span>
                </li>
              </ul>
              <div className="mt-6 text-center">
                <a href="/institutions">
                  <button className="bg-white text-league-blue hover:bg-league-text hover:text-league-blue py-2 px-6 rounded">
                    Learn More
                  </button>
                </a>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default Homepage;