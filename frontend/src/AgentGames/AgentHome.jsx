import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import Footer from '../Footer';
import { imageUrl } from '../config/assets';
import { featuredGames } from './Feedback/games';

const HOW_IT_WORKS_STEPS = [
  { time: "5 min", title: "Sign up and create a classroom" },
  { time: "5 min", title: "Select an agent game and its exercises" },
  { time: "5 min", title: "Invite students and watch them log in and progress" },
];

// The two showcase headings are full sentences, so from lg up they scale with
// the viewport instead of wrapping — one line, whatever the window width.
const SHOWCASE_HEADING =
  "text-2xl md:text-3xl font-bold text-ui-dark text-center mb-4 " +
  "lg:whitespace-nowrap lg:text-[clamp(0.9rem,1.4vw,1.5rem)]";

// Real product screenshots (hosted alongside the other assets on S3). All of
// them are captured at the same 1700x1050, so the tiles line up without any
// cropping and the click-to-zoom view shows them at their natural size.
const DASHBOARD_SHOTS = [
  {
    src: "teacher/dashboard-roster.png",
    title: "Class roster with progress at a glance",
    text: "Attempts, validated agents, hints used, ranking trend and exercise completion — one row per student.",
  },
  {
    src: "teacher/dashboard-progress.png",
    title: "Exercise-by-exercise progress grid",
    text: "See who passed what and who is stuck where, with attempt counts on the exercises that need another look.",
  },
  {
    src: "teacher/dashboard-submissions.png",
    title: "Every agent submission",
    text: "Read each student's code and how it evolved, submission by submission — with one-click plagiarism checks.",
  },
];

const STUDENT_SHOTS = [
  {
    src: "student/student-lesson.png",
    title: "Lessons with runnable code",
    text: "Concepts open next to the exercise, and every example is editable and runs in a sandbox — students try an idea without losing their place.",
  },
  {
    src: "student/student-hint.png",
    title: "A hint when the error is in the way",
    text: "Stuck on a syntax error? The hint points at the offending line and asks a question first — the full explanation stays one click away.",
  },
  {
    src: "student/student-feedback.png",
    title: "Submit an agent, watch it compete",
    text: "Every submission plays a full set of games straight away: where the agent placed, and a round-by-round replay of the decisions it made.",
  },
];

// Click-to-zoom for the screenshot tiles: the shots are 1700px wide, which is
// the size the overlay shows them at on a big screen.
const ShotLightbox = ({ shot, onClose }) => {
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4 cursor-zoom-out"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={shot.title}
    >
      <img
        src={imageUrl(shot.src)}
        alt={shot.title}
        className="w-full max-w-[1700px] max-h-full h-auto object-contain rounded-lg shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      />
      <button
        type="button"
        onClick={onClose}
        aria-label="Close"
        className="absolute top-4 right-6 text-white text-4xl leading-none hover:text-league-text"
      >
        ×
      </button>
    </div>
  );
};

const ShotGrid = ({ shots, onZoom }) => (
  <div className="grid md:grid-cols-3 gap-6">
    {shots.map((shot) => (
      <figure key={shot.src}>
        <button
          type="button"
          onClick={() => onZoom(shot)}
          className="block w-full cursor-zoom-in"
          aria-label={`Enlarge: ${shot.title}`}
        >
          <img
            src={imageUrl(shot.src)}
            alt={shot.title}
            className="w-full h-auto rounded-lg shadow-lg border border-ui-light"
          />
        </button>
        <figcaption className="text-center text-sm text-ui mt-3">
          {shot.text}
        </figcaption>
      </figure>
    ))}
  </div>
);

const Homepage = () => {
  const [zoomed, setZoomed] = useState(null);

  return (
    <div className="min-h-screen bg-ui-lighter pt-12">
      {/* Hero Section */}
      <section className="bg-gradient-to-br from-league-blue to-primary py-6">
        <div className="container mx-auto px-6 text-center">
          <h1 className="text-4xl md:text-5xl font-bold text-white mb-3">
            Python Programming Gamified
          </h1>
          <p className="text-lg text-league-text max-w-3xl mx-auto mb-5">
            Your students program agents that battle in strategic games — with
            guided tutorials, instant feedback, and live leaderboards. Set up
            your classroom in minutes.
          </p>
          <div className="flex flex-col md:flex-row justify-center gap-4">
            <Link to="/Demo" className="inline-block">
              <button className="bg-success hover:bg-success-hover text-white shadow-lg text-lg py-2.5 px-8 rounded">
                Try the Demo
              </button>
            </Link>
            <Link to="/Teachers" className="inline-block">
              <button className="bg-white text-primary hover:bg-league-text hover:text-primary-dark shadow-lg text-lg py-2.5 px-8 rounded">
                Create Your Classroom
              </button>
            </Link>
            <Link to="/Institutions" className="inline-block">
              <button className="bg-blue-200 text-primary-dark hover:bg-blue-300 shadow-lg text-lg py-2.5 px-8 rounded">
                Create a Coding Competition
              </button>
            </Link>
          </div>
          <p className="mt-4 text-league-text">
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
      <section className="py-5">
        <div className="container mx-auto px-6">
          <h2 className="text-2xl md:text-3xl font-bold text-ui-dark text-center mb-4">
            Up and Running in 15 minutes
          </h2>
          <div className="grid md:grid-cols-3 gap-4 max-w-5xl mx-auto">
            {HOW_IT_WORKS_STEPS.map((item) => (
              <div
                key={item.title}
                className="bg-white p-4 rounded-lg shadow-md flex items-center gap-3"
              >
                <span className="flex-shrink-0 text-sm font-bold text-primary-dark bg-blue-100 px-3 py-1 rounded-full">
                  {item.time}
                </span>
                <h3 className="text-base font-semibold text-ui-dark">
                  {item.title}
                </h3>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Teacher Dashboard — real product screenshots, side by side */}
      <section className="py-6 bg-ui-lighter">
        <div className="container mx-auto px-6">
          <h2 className={SHOWCASE_HEADING}>
            Teachers see who needs help and who needs extension
          </h2>
          <ShotGrid shots={DASHBOARD_SHOTS} onZoom={setZoomed} />
        </div>
      </section>

      {/* Student experience — the same product, from the student's side */}
      <section className="py-6 bg-white">
        <div className="container mx-auto px-6">
          <h2 className={SHOWCASE_HEADING}>
            <span className="block">
              Students complete short courses and exercises
            </span>
            <span className="block">
              Then program agents that win at games of strategy
            </span>
          </h2>
          <ShotGrid shots={STUDENT_SHOTS} onZoom={setZoomed} />
        </div>
      </section>

      {/* Child Safe & Responsible AI Section */}
      <section className="py-16 bg-white">
        <div className="container mx-auto px-6">
          <h2 className="text-3xl font-bold text-ui-dark text-center mb-12">
            Safe and Responsible by Design
          </h2>
          <div className="grid md:grid-cols-2 gap-8 max-w-5xl mx-auto">
            {/* Child Safe */}
            <div className="bg-ui-lighter p-8 rounded-lg shadow-md border-t-4 border-success">
              <div className="flex items-center mb-4">
                <div className="w-12 h-12 rounded-full bg-success-light flex items-center justify-center mr-4 flex-shrink-0">
                  <svg
                    className="w-7 h-7 text-success"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                    />
                  </svg>
                </div>
                <h3 className="text-xl font-semibold text-ui-dark">Child Safe</h3>
              </div>
              <ul className="space-y-3 text-ui">
                {[
                  "No student emails or personal information stored",
                  "No chat interfaces for students",
                  "All student activity on the platform viewable from the teacher dashboard",
                ].map((point) => (
                  <li key={point} className="flex items-start">
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
                    <span>{point}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* AI Enhancing not replacing learning */}
            <div className="bg-ui-lighter p-8 rounded-lg shadow-md border-t-4 border-primary">
              <div className="flex items-center mb-4">
                <div className="w-12 h-12 rounded-full bg-primary-light flex items-center justify-center mr-4 flex-shrink-0">
                  <svg
                    className="w-7 h-7 text-primary"
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
                <h3 className="text-xl font-semibold text-ui-dark">
                  AI Enhancing, Not Replacing Learning
                </h3>
              </div>
              <ul className="space-y-3 text-ui">
                {[
                  "When students are stuck and not making progress, an AI hint is provided",
                  "Students spend more time focusing on reasoning and algorithmic thinking",
                  "AI removes some friction around syntax errors, indentation and bugs"
                ].map((point) => (
                  <li key={point} className="flex items-start">
                    <svg
                      className="w-5 h-5 text-primary mt-0.5 mr-2 flex-shrink-0"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fillRule="evenodd"
                        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                        clipRule="evenodd"
                      />
                    </svg>
                    <span>{point}</span>
                  </li>
                ))}
              </ul>
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
                    onClick={() =>
                      setZoomedImage({
                        src: imageUrl(game.thumbnail),
                        alt: `${game.displayName} game`,
                      })
                    }
                    className="w-full h-48 object-cover cursor-zoom-in transition-transform hover:scale-[1.02]"
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

      {zoomed && <ShotLightbox shot={zoomed} onClose={() => setZoomed(null)} />}
    </div>
  );
};

export default Homepage;
