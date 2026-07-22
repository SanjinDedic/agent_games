import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import {
  logout,
  selectCurrentUser,
  selectIsAuthenticated,
} from './slices/authSlice';
import { clearTeam } from './slices/teamsSlice';
import { clearResults, clearLeagues } from './slices/leaguesSlice';
import { selectImmersiveMode } from './slices/settingsSlice';
import { Button } from './components/ui';
import { useTerms } from './AgentGames/Shared/terminology';

// User-visible entity labels come from terminology.js (the `T` map): teacher
// accounts see "Students"/"Short Course", everyone else "Teams"/"Tutorial".
// Routes, admin-section labels, and marketing copy stay literal.
function getNavLinks(T) {
  return {
    admin: [
      { to: "/AdminInstitutions", label: "Institutions" },
      { to: "/AdminDockerStatus", label: "Service Status" },
      { to: "/AdminBackup", label: "Backups" },
      { to: "/AdminAPIKeys", label: "API Keys" },
      { to: "/AdminUserSupport", label: "User Support" },
      { to: "/AdminTutorials", label: "Tutorials" },
      { to: "/AdminLessons", label: "Lessons" },
    ],
    // Everything about one league/classroom lives in the /Classroom/:id
    // workspace, entered from the Home cards; the navbar only keeps Home and
    // the institution-wide directory (the sole surface for unassigned members).
    // Teacher and competition institutions share these routes — `T.Teams`
    // renders "Students" vs "Teams" from the account's own terminology.
    institution: [
      { to: "/InstitutionHome", label: "Home" },
      { to: "/InstitutionTeam", label: T.Teams },
    ],
    team: [
      { to: "/TeamHome", label: "Home" },
      { to: "/AgentSubmission", label: "Submit Agent" },
      { to: "/Tutorial", label: T.Tutorial },
      { to: "/Leaderboards", label: "Leaderboards" },
    ],
    demo: [
      { to: "/TeamHome", label: "Home" },
      { to: "/AgentSubmission", label: "Submit Agent" },
      { to: "/Tutorial", label: T.Tutorial },
    ],
    // Logged-out visitors get the teacher-first pitch. Navbar links go to the
    // login pages (returning users); the home-page hero carries the signup CTAs,
    // and each login page links back to its signup/pricing page.
    public: [
      { to: "/Demo", label: "Demo" },
      { to: "/Teacher", label: "For Teachers" },
      { to: "/Institution", label: "For Competitions" },
    ],
  };
}

function resolveNavGroup(currentUser, isAuthenticated) {
  if (!isAuthenticated) return "public";
  const role = currentUser?.role;
  if (role === "admin") return "admin";
  if (role === "institution") return "institution";
  if (role === "student") return currentUser?.is_demo ? "demo" : "team";
  return "public";
}

function AgentGamesNavbar() {
  const navigate = useNavigate();
  const dispatch = useDispatch();

  const currentUser = useSelector(selectCurrentUser);
  const isAuthenticated = useSelector(selectIsAuthenticated);
  const isImmersive = useSelector(selectImmersiveMode);
  const T = useTerms();
  const userRole = currentUser?.role || "";
  const navGroup = resolveNavGroup(currentUser, isAuthenticated);
  const navLinks = getNavLinks(T)[navGroup];

  const [repoStats, setRepoStats] = useState(() => {
    try {
      const cached = sessionStorage.getItem("github:SanjinDedic/agent_games");
      return cached ? JSON.parse(cached) : null;
    } catch {
      return null;
    }
  });

  useEffect(() => {
    let cancelled = false;
    fetch("https://api.github.com/repos/SanjinDedic/agent_games")
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((data) => {
        if (cancelled) return;
        const stats = {
          stars: data.stargazers_count,
          forks: data.forks_count,
        };
        setRepoStats(stats);
        try {
          sessionStorage.setItem(
            "github:SanjinDedic/agent_games",
            JSON.stringify(stats)
          );
        } catch {
          /* ignore quota errors */
        }
      })
      .catch(() => {
        /* keep cached/null values on failure */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const handleLogout = () => {
    dispatch(logout());
    dispatch(clearLeagues());
    dispatch(clearTeam());
    dispatch(clearResults());

    // Redirect based on role
    if (userRole === "admin") {
      navigate("/Admin");
    } else if (userRole === "institution") {
      navigate(currentUser?.is_teacher ? "/Teacher" : "/Institution");
    } else if (currentUser?.is_demo) {
      // Demo sessions are account-less — send them back to the home page,
      // not a login page they can't use.
      navigate("/");
    } else {
      navigate("/AgentLogin");
    }
  };

  const navLinkClasses = "inline-flex items-center px-3 py-3 text-lg text-white hover:bg-white/10 transition-colors duration-200";

  // Immersive mode (submission workspaces) reclaims the navbar's screen space
  if (isImmersive) return null;

  return (
    <nav className="bg-[#111827] fixed top-0 w-full z-50">
      <div className="w-full mx-auto px-4">
        <div className="flex justify-between items-center">
          {/* Left side - brand + role-specific links */}
          <div className="flex items-center gap-2">
            <Link
              to="/"
              className="inline-flex items-center px-3 py-3 text-lg font-bold text-white hover:bg-white/10 transition-colors duration-200"
            >
              Agent Games
            </Link>
            {navLinks.map((link) => (
              <Link key={link.to} to={link.to} className={navLinkClasses}>
                {link.label}
              </Link>
            ))}
          </div>

          {/* Right side - GitHub info and logout */}
          <div className="flex items-center">
            {/* GitHub Repo Info */}
            <span className="ml-4 text-white text-sm font-medium">
              Open Source
            </span>
            <a
              href="https://github.com/SanjinDedic/agent_games"
              className="flex items-center text-white hover:text-gray-200 transition-colors duration-200 ml-4"
              target="_blank"
              rel="noopener noreferrer"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 480 512"
                className="w-5 h-5 mr-2"
              >
                <path
                  fill="currentColor"
                  d="M186.1 328.7c0 20.9-10.9 55.1-36.7 55.1s-36.7-34.2-36.7-55.1 10.9-55.1 36.7-55.1 36.7 34.2 36.7 55.1zM480 278.2c0 31.9-3.2 65.7-17.5 95-37.9 76.6-142.1 74.8-216.7 74.8-75.8 0-186.2 2.7-225.6-74.8-14.6-29-20.2-63.1-20.2-95 0-41.9 13.9-81.5 41.5-113.6-5.2-15.8-7.7-32.4-7.7-48.8 0-21.5 4.9-32.3 14.6-51.8 45.3 0 74.3 9 108.8 36 29-6.9 58.8-10 88.7-10 27 0 54.2 2.9 80.4 9.2 34-26.7 63-35.2 107.8-35.2 9.8 19.5 14.6 30.3 14.6 51.8 0 16.4-2.6 32.7-7.7 48.2 27.5 32.4 39 72.3 39 114.2zm-64.3 50.5c0-43.9-26.7-82.6-73.5-82.6-18.9 0-37 3.4-56 6-14.9 2.3-29.8 3.2-45.1 3.2-15.2 0-30.1-.9-45.1-3.2-18.7-2.6-37-6-56-6-46.8 0-73.5 38.7-73.5 82.6 0 87.8 80.4 101.3 150.4 101.3h48.2c70.3 0 150.6-13.4 150.6-101.3zm-82.6-55.1c-25.8 0-36.7 34.2-36.7 55.1s10.9 55.1 36.7 55.1 36.7-34.2 36.7-55.1-10.9-55.1-36.7-55.1z"
                ></path>
              </svg>
              <div className="flex flex-col">
                <span className="text-sm font-medium">
                  SanjinDedic/agent_games
                </span>
                <ul className="flex text-xs space-x-3">
                  <li>★ {repoStats?.stars ?? "…"}</li>
                  <li>🍴 {repoStats?.forks ?? "…"}</li>
                </ul>
              </div>
            </a>

            {/* Logout Button for any authenticated user */}
            {isAuthenticated && (
              <Button variant="danger" onClick={handleLogout} className="ml-4">
                Logout
              </Button>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}

export default AgentGamesNavbar;
