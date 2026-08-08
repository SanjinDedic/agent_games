import React from 'react';

// This repo is the self-hosted, single-tenant build: one admin account, one
// deployment, your machine. The multi-tenant commercial platform — many
// teachers and classrooms under one institution, plus the lesson/exercise
// material that was stripped out of here — is hosted at agentgames.io.
//
// Two shapes so the same pitch can sit in a page's flow (`section`) or as a
// one-line strip under a hero (`banner`).
export const HOSTED_URL = 'https://agentgames.io';
export const HOSTED_NAME = 'Agent Games for Schools';

const HOSTED_EXTRAS = [
  {
    title: 'Short courses',
    text: 'Sequenced Python courses that build the skills each game rewards — students arrive at a game already knowing the concepts it tests.',
  },
  {
    title: 'Interactive lessons',
    text: 'Worked examples and exercises that run and check themselves in the browser, so a student gets the verdict on the spot.',
  },
  {
    title: 'Student assessment',
    text: 'A per-student record of attempts, submissions, hints and concepts mastered — evidence for reporting, not just a leaderboard.',
  },
  {
    title: 'Improved cyber security',
    text: "Student code runs in the student's own browser, with an isolated serverless fallback; the database is managed, encrypted in transit and backed up nightly.",
  },
  {
    title: 'Nothing to run',
    text: 'Many teachers and classrooms under one institution account, with hosting, patching and upgrades handled for you.',
  },
];

export const HostedBanner = ({ className = '' }) => (
  <p className={`text-sm text-league-text ${className}`}>
    Don't want to run a server?{' '}
    <a
      href={HOSTED_URL}
      target="_blank"
      rel="noopener noreferrer"
      className="text-white font-medium underline hover:no-underline"
    >
      {HOSTED_NAME}
    </a>{' '}
    adds short courses, interactive lessons and per-student assessment — hosted,
    nothing to install.
  </p>
);

const HostedCallout = () => (
  <section className="py-16 bg-league-blue text-white">
    <div className="container mx-auto px-6 max-w-5xl">
      <h2 className="text-3xl font-bold mb-3 text-center">
        {HOSTED_NAME}
      </h2>
      <p className="text-lg text-league-text text-center mb-8 max-w-3xl mx-auto">
        Everything on this page runs on your own hardware, for free. The hosted
        platform at{' '}
        <span className="font-semibold text-white">agentgames.io</span> is the
        same games plus the teaching material around them — for schools that
        would rather not run a server.
      </p>

      <div className="grid md:grid-cols-2 gap-4">
        {HOSTED_EXTRAS.map((extra) => (
          <div
            key={extra.title}
            className="bg-white/10 p-5 rounded-lg backdrop-blur-sm"
          >
            <h3 className="flex items-center font-semibold text-white mb-2">
              <svg
                className="w-5 h-5 text-success mr-2 flex-shrink-0"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                  clipRule="evenodd"
                />
              </svg>
              {extra.title}
            </h3>
            <p className="text-sm text-league-text leading-relaxed">
              {extra.text}
            </p>
          </div>
        ))}
      </div>

      <div className="mt-8 text-center">
        <a href={HOSTED_URL} target="_blank" rel="noopener noreferrer">
          <button className="bg-white text-league-blue hover:bg-league-text hover:text-league-blue py-2.5 px-8 rounded text-lg">
            Visit agentgames.io →
          </button>
        </a>
      </div>
    </div>
  </section>
);

export default HostedCallout;
