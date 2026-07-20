import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useSelector } from 'react-redux';

import Footer from '../Footer';
import { imageUrl } from '../config/assets';
import { featuredGames } from './Feedback/games';

const HOW_IT_WORKS_STEPS = [
  {
    step: "1",
    title: "Create your classroom",
    text: "Sign up as a teacher and set up a classroom in minutes — no installs, no student emails.",
  },
  {
    step: "2",
    title: "Share one link",
    text: "Every classroom has its own login page. Students sign up and log in there, and always land in the right place.",
  },
  {
    step: "3",
    title: "Watch them compete",
    text: "Students learn Python with guided tutorials, then submit agents that battle on a live leaderboard.",
  },
];

const Homepage = () => {
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const [contentOverview, setContentOverview] = useState(null);

  // Live tutorial/lesson counts for the hero strip
  useEffect(() => {
    let cancelled = false;
    fetch(`${apiUrl}/demo/content_overview`)
      .then((response) => (response.ok ? response.json() : null))
      .then((data) => {
        if (!cancelled && data) setContentOverview(data);
      })
      .catch(() => {
        // Informational strip only — omit it if the fetch fails
      });
    return () => {
      cancelled = true;
    };
  }, [apiUrl]);

  return (
    <div className="min-h-screen bg-ui-lighter pt-12">
      {/* Hero Section */}
      <section className="bg-gradient-to-br from-league-blue to-primary py-20">
        <div className="container mx-auto px-6 text-center">
          <h1 className="text-4xl md:text-6xl font-bold text-white mb-6">
            Python Programming Gamified
          </h1>
          <p className="text-xl text-league-text max-w-3xl mx-auto mb-10">
            Your students program agents that battle in strategic games — with
            guided tutorials, instant feedback, and live leaderboards. Set up
            your classroom in minutes.
          </p>
          {contentOverview && (
            <div className="flex justify-center gap-10 mb-10">
              <div className="text-center">
                <p className="text-4xl font-bold text-white">
                  {contentOverview.total_tutorials}
                </p>
                <p className="text-league-text">Guided Tutorials</p>
              </div>
              <div className="text-center">
                <p className="text-4xl font-bold text-white">
                  {contentOverview.total_lessons}
                </p>
                <p className="text-league-text">Python Lessons</p>
              </div>
              <div className="text-center">
                <p className="text-4xl font-bold text-white">
                  {featuredGames.length}
                </p>
                <p className="text-league-text">Strategy Games</p>
              </div>
            </div>
          )}
          <div className="flex flex-col md:flex-row justify-center gap-4">
            <Link to="/Demo" className="inline-block">
              <button className="bg-success hover:bg-success-hover text-white shadow-lg text-xl py-3 px-8 rounded">
                Try the Demo
              </button>
            </Link>
            <Link to="/Teachers" className="inline-block">
              <button className="bg-white text-primary hover:bg-league-text hover:text-primary-dark shadow-lg text-xl py-3 px-8 rounded">
                Create Your Classroom
              </button>
            </Link>
            <Link to="/Institutions" className="inline-block">
              <button className="border-2 border-white text-white hover:bg-white hover:text-primary shadow-lg text-xl py-3 px-8 rounded">
                Create a Coding Competition
              </button>
            </Link>
          </div>
          <p className="mt-8 text-league-text">
            Students: open the classroom link your teacher shared, or{" "}
            <Link
              to="/AgentLogin"
              className="text-white font-medium underline hover:no-underline"
            >
              log in here
            </Link>
            .
          </p>
        </div>
      </section>

      {/* How It Works Section */}
      <section className="py-16">
        <div className="container mx-auto px-6">
          <h2 className="text-3xl font-bold text-ui-dark text-center mb-12">
            Up and Running in One Lesson
          </h2>
          <div className="grid md:grid-cols-3 gap-8">
            {HOW_IT_WORKS_STEPS.map((item) => (
              <div key={item.step} className="bg-white p-6 rounded-lg shadow-md">
                <div className="w-14 h-14 rounded-full bg-primary-light flex items-center justify-center mb-4">
                  <span className="text-2xl font-bold text-primary">
                    {item.step}
                  </span>
                </div>
                <h3 className="text-xl font-semibold text-ui-dark mb-2">
                  {item.title}
                </h3>
                <p className="text-ui">{item.text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-16 bg-white">
        <div className="container mx-auto px-6">
          <h2 className="text-3xl font-bold text-ui-dark text-center mb-12">
            Why Agent Games?
          </h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            {/* Feature 1 */}
            <div className="bg-ui-lighter p-6 rounded-lg shadow-md">
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
                Real Algorithmic Thinking
              </h3>
              <p className="text-ui">
                Students program agents that make strategic decisions,
                developing algorithm design and problem-solving skills that
                worksheets never touch.
              </p>
            </div>

            {/* Feature 2 */}
            <div className="bg-ui-lighter p-6 rounded-lg shadow-md">
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
                Host a Contest in 5 Minutes
              </h3>
              <p className="text-ui">
                Live leaderboards, constant iteration, drama and deep learning
                — more engaging than anything else you can run in a computing
                class.
              </p>
            </div>

            {/* Feature 3 */}
            <div className="bg-ui-lighter p-6 rounded-lg shadow-md">
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
                    d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                  />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-ui-dark mb-2">
                Progress Tracking Built In
              </h3>
              <p className="text-ui">
                See who attempted and passed every tutorial exercise, and each
                student's recent leaderboard placements — one dashboard, no
                marking required.
              </p>
            </div>

            {/* Feature 4 */}
            <div className="bg-ui-lighter p-6 rounded-lg shadow-md">
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
                The platform is open source — clone the GitHub repo and host it
                yourself, or sign up for an affordable, hassle-free hosted
                account.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Games Section */}
      <section className="py-16">
        <div className="container mx-auto px-6">
          <h2 className="text-3xl font-bold text-ui-dark text-center mb-12">
            Featured Games
          </h2>
          <div className="grid md:grid-cols-3 gap-8">
            {featuredGames.map((game) => (
              <div
                key={game.name}
                className="bg-white p-6 rounded-lg shadow-md"
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
                <Link to={`/Demo?game=${game.name}`}>
                  <span className="text-primary font-medium hover:text-primary-hover">
                    Try it →
                  </span>
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* For Teachers Section */}
      <section className="py-16 bg-league-blue text-white">
        <div className="container mx-auto px-6">
          <div className="max-w-4xl mx-auto">
            <h2 className="text-3xl font-bold mb-6 text-center">
              Built for Teachers
            </h2>
            <p className="text-lg mb-8 text-league-text text-center">
              Agent Games gives you a ready-made way to teach programming and
              algorithmic thinking in a competitive, engaging environment —
              without any setup burden.
            </p>
            <div className="bg-white/10 p-6 rounded-lg backdrop-blur-sm">
              <h3 className="text-xl font-semibold mb-4">
                What you get with a classroom:
              </h3>
              <ul className="space-y-3 text-league-text">
                {[
                  "Structured Python tutorials with instant automated feedback",
                  "A shareable classroom login page — students join with one link",
                  "A progress dashboard: exercise completion and recent placements for every student",
                  "Automatic evaluation of student agents with live leaderboards",
                ].map((benefit) => (
                  <li key={benefit} className="flex items-start">
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
                    <span>{benefit}</span>
                  </li>
                ))}
              </ul>
              <div className="mt-6 text-center">
                <Link to="/Teachers">
                  <button className="bg-white text-league-blue hover:bg-league-text hover:text-league-blue py-2 px-6 rounded">
                    Create Your Classroom
                  </button>
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Competitions Strip */}
      <section className="py-12 bg-white">
        <div className="container mx-auto px-6 text-center">
          <h2 className="text-2xl font-bold text-ui-dark mb-3">
            Running a Coding Competition?
          </h2>
          <p className="text-ui max-w-2xl mx-auto mb-6">
            Agent Games also powers inter-school and university tournaments —
            team signup links, sandboxed code execution, and instant published
            results.
          </p>
          <Link
            to="/Institutions"
            className="text-primary font-medium hover:text-primary-hover text-lg"
          >
            Learn about hosting competitions →
          </Link>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default Homepage;
