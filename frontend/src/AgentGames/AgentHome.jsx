import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import Footer from '../Footer';
import { imageUrl, videoUrl } from '../config/assets';
import { gamesList } from './Feedback/games';
import { useTerms } from './Shared/terminology';
import HostedCallout, { HostedBanner } from './Shared/Common/HostedCallout';

// The whole pitch of this build: `docker compose up` is the install. The block
// is copyable in one click because that is the first thing a visitor does.
const QUICKSTART = `git clone https://github.com/SanjinDedic/agent_games.git
cd agent_games
docker compose up --build`;

const QUICKSTART_STEPS = [
  {
    time: "1 min",
    title: "Install Docker",
    text: "The only prerequisite. No Python, Node or database to set up — every service runs in a container.",
  },
  {
    time: "3 min",
    title: "Clone and start",
    text: "The committed .env holds working local defaults, so there is nothing to configure before the first run.",
  },
  {
    time: "1 min",
    title: "Claim the deployment",
    text: "A fresh install has no accounts. Open /Login, create the single admin account, and start making leagues.",
  },
];

const SELF_HOST_POINTS = [
  {
    title: "One admin, one deployment",
    text: "No tenants, no sign-up flow, no billing. The first person to open /Login claims the install and runs everything from there.",
  },
  {
    title: "Your data stays yours",
    text: "Submissions and results live in the Postgres container next to the app. Nothing phones home.",
  },
  {
    title: "Submitted code runs sandboxed",
    text: "An AST safety check before the queue, then a fresh worker process per task, capped at 500MB and 50 processes with hard time limits.",
  },
  {
    title: "Bring your own AI key",
    text: "AI hints and plagiarism checks are optional. Paste an OpenAI, Anthropic or Google key in the admin's API Keys page, or leave them off.",
  },
  {
    title: "Eight games, or write your own",
    text: "Drop three files in backend/games/<name>/ and a manifest folder in the frontend — both sides discover it on restart.",
  },
  {
    title: "Open source, AGPL-3.0",
    text: "Read it, fork it, run it on a laptop for one class or on a small VPS for a whole competition.",
  },
];

const WHAT_RUNS = [
  { port: "3000", label: "Frontend", detail: "React SPA with the in-browser editor" },
  { port: "8000", label: "API", detail: "FastAPI, plus interactive docs at /docs" },
  { port: "5432", label: "Postgres", detail: "Schema built and migrated on boot" },
  { port: "6379", label: "Valkey", detail: "Queue for the validation and simulation workers" },
];

// Real product screenshots (hosted alongside the other assets on S3). All of
// them are captured at the same 1700x1050, so the tiles line up without any
// cropping and the click-to-zoom view shows them at their natural size.
//
// The objects are served with max-age=86400, so re-shooting them leaves anyone
// who visited that day on a mix of old and new files — bump ?v when they are
// replaced.
const PRODUCT_SHOTS = [
  {
    src: "teacher/dashboard-roster.png?v=2",
    title: "Roster with progress at a glance",
    text: "Attempts, validated agents, hints used and ranking trend — one row per member of a league.",
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

// A game tile that degrades to a named placeholder when its screenshot is
// missing from the assets bucket (not every game has been shot yet)
const GameThumb = ({ game }) => {
  const [broken, setBroken] = useState(false);
  if (broken) {
    return (
      <div className="w-full h-48 flex items-center justify-center bg-ui-dark text-white/60 text-2xl font-bold text-center px-4">
        {game.displayName}
      </div>
    );
  }
  return (
    <img
      src={imageUrl(game.thumbnail)}
      alt={`${game.displayName} game`}
      onError={() => setBroken(true)}
      className="w-full h-48 object-cover"
    />
  );
};

const CopyBlock = ({ code }) => {
  const [copied, setCopied] = useState(false);

  const copy = () => {
    // navigator.clipboard is unavailable over plain http on some browsers —
    // the commands stay selectable either way, so failure is silent.
    navigator.clipboard?.writeText(code).then(
      () => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      },
      () => {}
    );
  };

  // The clone line is wider than the column on most screens, so the Copy
  // control sits in its own bar rather than floating over scrolling text.
  return (
    <div className="rounded-lg overflow-hidden bg-[#111827]">
      <div className="flex items-center justify-between px-4 py-2 bg-white/5">
        <span className="text-xs uppercase tracking-wide text-white/50">
          bash
        </span>
        <button
          type="button"
          onClick={copy}
          className="text-xs bg-white/10 hover:bg-white/20 text-white px-3 py-1.5 rounded transition-colors"
        >
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre className="text-green-300 text-sm md:text-base px-5 py-4 overflow-x-auto">
        <code>{code}</code>
      </pre>
    </div>
  );
};

const Homepage = () => {
  const T = useTerms();
  const [zoomed, setZoomed] = useState(null);

  return (
    <div className="min-h-screen bg-ui-lighter pt-12">
      {/* Hero Section */}
      <section className="bg-gradient-to-br from-league-blue to-primary py-8">
        <div className="container mx-auto px-6 text-center">
          <h1 className="text-4xl md:text-5xl font-bold text-white mb-3">
            Python Agents That Compete — On Your Own Machine
          </h1>
          <p className="text-lg text-league-text max-w-3xl mx-auto mb-5">
            Agent Games is a self-hosted platform where {T.teams} write Python
            agents that battle in strategic games, with instant feedback and
            live leaderboards. Clone the repo, run one command, and the whole
            stack is up on localhost.
          </p>
          <div className="flex flex-col md:flex-row justify-center gap-4">
            <a href="#quickstart" className="inline-block">
              <button className="bg-white text-primary hover:bg-league-text hover:text-primary-dark shadow-lg text-lg py-2.5 px-8 rounded">
                Run it locally
              </button>
            </a>
            <Link to="/Login" className="inline-block">
              <button className="bg-blue-200 text-primary-dark hover:bg-blue-300 shadow-lg text-lg py-2.5 px-8 rounded">
                Admin login
              </button>
            </Link>
            <Link to="/AgentLogin" className="inline-block">
              <button className="bg-blue-200 text-primary-dark hover:bg-blue-300 shadow-lg text-lg py-2.5 px-8 rounded">
                {`${T.Team} login`}
              </button>
            </Link>
          </div>
          <HostedBanner className="mt-5" />
        </div>
      </section>

      {/* Quickstart — the commands, next to the walkthrough video */}
      <section id="quickstart" className="py-12 scroll-mt-16">
        <div className="container mx-auto px-6">
          <h2 className="text-2xl md:text-3xl font-bold text-ui-dark text-center mb-2">
            Up and Running in 5 Minutes
          </h2>
          <p className="text-ui text-center mb-8">
            Docker is the only prerequisite. Everything else is in the repo.
          </p>

          <div className="grid lg:grid-cols-2 gap-8 items-start max-w-6xl mx-auto">
            <div>
              <CopyBlock code={QUICKSTART} />
              <p className="text-ui mt-4">
                Then open{" "}
                <a
                  href="http://localhost:3000"
                  className="text-primary font-medium hover:text-primary-hover"
                >
                  localhost:3000
                </a>{" "}
                and claim the deployment at <code>/Login</code> — the first-run
                form creates the one admin account. No seeded passwords, no
                sign-up emails.
              </p>

              <div className="grid sm:grid-cols-2 gap-3 mt-6">
                {WHAT_RUNS.map((service) => (
                  <div
                    key={service.port}
                    className="bg-white rounded-lg shadow-sm border border-ui-light p-3"
                  >
                    <div className="flex items-baseline gap-2">
                      <span className="text-xs font-mono font-bold text-primary-dark bg-blue-100 px-2 py-0.5 rounded">
                        :{service.port}
                      </span>
                      <span className="font-semibold text-ui-dark">
                        {service.label}
                      </span>
                    </div>
                    <p className="text-sm text-ui mt-1">{service.detail}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-md overflow-hidden">
              <div className="aspect-video bg-black">
                <video
                  controls
                  preload="metadata"
                  className="w-full h-full"
                  src={videoUrl('run_locally.mp4')}
                />
              </div>
              <div className="p-4">
                <h3 className="text-xl font-semibold text-ui-dark mb-1">
                  Watch the install, start to finish
                </h3>
                <p className="text-ui text-sm">
                  A five-minute walk-through: clone, start the stack, create the
                  admin account, and run a first simulation.
                </p>
              </div>
            </div>
          </div>

          <div className="grid md:grid-cols-3 gap-4 max-w-5xl mx-auto mt-10">
            {QUICKSTART_STEPS.map((step) => (
              <div
                key={step.title}
                className="bg-white p-4 rounded-lg shadow-md"
              >
                <div className="flex items-center gap-3 mb-2">
                  <span className="flex-shrink-0 text-sm font-bold text-primary-dark bg-blue-100 px-3 py-1 rounded-full">
                    {step.time}
                  </span>
                  <h3 className="text-base font-semibold text-ui-dark">
                    {step.title}
                  </h3>
                </div>
                <p className="text-sm text-ui">{step.text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* What self-hosting gets you */}
      <section className="py-14 bg-white">
        <div className="container mx-auto px-6">
          <h2 className="text-2xl md:text-3xl font-bold text-ui-dark text-center mb-10">
            One Deployment, Fully Under Your Control
          </h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
            {SELF_HOST_POINTS.map((point) => (
              <div
                key={point.title}
                className="bg-ui-lighter p-6 rounded-lg border-t-4 border-primary shadow-sm"
              >
                <h3 className="text-lg font-semibold text-ui-dark mb-2">
                  {point.title}
                </h3>
                <p className="text-ui text-sm leading-relaxed">{point.text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* The product itself — real screenshots from a running instance */}
      <section className="py-12">
        <div className="container mx-auto px-6">
          <h2 className="text-2xl md:text-3xl font-bold text-ui-dark text-center mb-8">
            What It Looks Like Once It's Running
          </h2>
          <ShotGrid shots={PRODUCT_SHOTS} onZoom={setZoomed} />
        </div>
      </section>

      {/* Games Section — every game in the repo, not a featured subset */}
      <section className="py-14 bg-white">
        <div className="container mx-auto px-6">
          <h2 className="text-2xl md:text-3xl font-bold text-ui-dark text-center mb-3">
            {gamesList.length} Games Included
          </h2>
          <p className="text-ui text-center mb-10">
            All of them ship in the repo and are auto-discovered on startup.
          </p>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {gamesList.map((game) => (
              <div
                key={game.name}
                className="bg-ui-lighter rounded-lg shadow-md overflow-hidden flex flex-col"
              >
                <Link to={`/GamePreview/${game.name}`}>
                  <GameThumb game={game} />
                </Link>
                <div className="p-5 flex flex-col flex-1">
                  <h3 className="text-lg font-semibold text-ui-dark mb-2">
                    {game.displayName}
                  </h3>
                  <p className="text-ui text-sm mb-4 flex-1">
                    {game.description}
                  </p>
                  <Link to={`/GamePreview/${game.name}`}>
                    <span className="text-primary font-medium hover:text-primary-hover">
                      Preview →
                    </span>
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <HostedCallout />

      <Footer />

      {zoomed && <ShotLightbox shot={zoomed} onClose={() => setZoomed(null)} />}
    </div>
  );
};

export default Homepage;
