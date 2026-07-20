import React from 'react';
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

const NAV_LINKS_BY_ROLE = {
  admin: [
    { to: "/AdminInstitutions", label: "Institutions" },
    { to: "/AdminDockerStatus", label: "Service Status" },
    { to: "/AdminBackup", label: "Backups" },
    { to: "/AdminAPIKeys", label: "API Keys" },
    { to: "/AdminUserSupport", label: "User Support" },
    { to: "/AdminTutorials", label: "Tutorials" },
    { to: "/AdminLessons", label: "Lessons" },
  ],
  institution: [
    { to: "/InstitutionTeam", label: "Team Section" },
    { to: "/InstitutionProgress", label: "Team Progress" },
    { to: "/InstitutionLeague", label: "League Management" },
    { to: "/InstitutionLeagueSimulation", label: "League Simulation" },
    { to: "/InstitutionSubscription", label: "Subscription" },
  ],
  // Teacher accounts share the institution routes; only the wording changes.
  teacher: [
    { to: "/InstitutionTeam", label: "Student Section" },
    { to: "/InstitutionProgress", label: "Student Progress" },
    { to: "/InstitutionLeague", label: "Classroom Management" },
    { to: "/InstitutionLeagueSimulation", label: "Classroom Simulation" },
    { to: "/InstitutionSubscription", label: "Subscription" },
  ],
  team: [
    { to: "/TeamHome", label: "Home" },
    { to: "/AgentSubmission", label: "Submit Agent" },
    { to: "/Tutorial", label: "Tutorial" },
    { to: "/Leaderboards", label: "Leaderboards" },
  ],
  demo: [
    { to: "/TeamHome", label: "Home" },
    { to: "/AgentSubmission", label: "Submit Agent" },
    { to: "/Tutorial", label: "Tutorial" },
  ],
  // Logged-out visitors get the teacher-first pitch; everything else
  // (About, Leaderboards) lives on the home page and footer.
  public: [
    { to: "/Demo", label: "Demo" },
    { to: "/Teachers", label: "For Teachers" },
    { to: "/Institutions", label: "For Competitions" },
  ],
};

function resolveNavGroup(currentUser, isAuthenticated) {
  if (!isAuthenticated) return "public";
  const role = currentUser?.role;
  if (role === "admin") return "admin";
  if (role === "institution") return currentUser?.is_teacher ? "teacher" : "institution";
  if (role === "student") return currentUser?.is_demo ? "demo" : "team";
  return "public";
}

function AgentGamesNavbar() {
  const navigate = useNavigate();
  const dispatch = useDispatch();

  const currentUser = useSelector(selectCurrentUser);
  const isAuthenticated = useSelector(selectIsAuthenticated);
  const isImmersive = useSelector(selectImmersiveMode);
  const userRole = currentUser?.role || "";
  const navGroup = resolveNavGroup(currentUser, isAuthenticated);
  const navLinks = NAV_LINKS_BY_ROLE[navGroup];

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

          {/* Right side - session action */}
          <div className="flex items-center">
            {isAuthenticated ? (
              <Button variant="danger" onClick={handleLogout} className="ml-4">
                Logout
              </Button>
            ) : (
              <Link
                to="/AgentLogin"
                className="ml-4 my-1.5 py-2 px-5 text-lg font-medium text-white bg-primary hover:bg-primary-hover rounded transition-colors duration-200"
              >
                Log in
              </Link>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}

export default AgentGamesNavbar;
