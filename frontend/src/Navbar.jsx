import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { logout } from './slices/authSlice';
import { clearTeam } from './slices/teamsSlice';
import { clearResults, clearLeagues } from './slices/leaguesSlice';
import { Button } from './components/ui';

function AgentGamesNavbar() {
  const location = useLocation();
  const navigate = useNavigate();
  const dispatch = useDispatch();

  const adminRoutes = [
    "/AdminLeague",
    "/AdminLeagueSimulation",
    "/AdminDockerStatus",
    "/AdminDemoUsers",
    "/AdminInstitutions",
  ];
  const institutionRoutes = [
    "/InstitutionTeam",
    "/InstitutionLeague",
    "/InstitutionLeagueSimulation",
  ];
  
  const isAdminRoute = adminRoutes.includes(location.pathname);
  const isInstitutionRoute = institutionRoutes.includes(location.pathname);
  const currentUser = useSelector((state) => state.auth.currentUser);
  const userRole = currentUser?.role || "";

  const handleLogout = () => {
    dispatch(logout());
    dispatch(clearLeagues());
    dispatch(clearTeam());
    dispatch(clearResults());

    // Redirect based on role
    if (userRole === "admin") {
      navigate("/Admin");
    } else if (userRole === "institution") {
      navigate("/Institution");
    } else {
      navigate("/AgentLogin");
    }
  };

  const navLinkClasses = "inline-flex items-center px-3 py-3 text-lg text-white hover:bg-white/10 transition-colors duration-200";

  return (
    <nav className="bg-[#111827] fixed top-0 w-full z-50">
      <div className="w-full mx-auto px-4">
        <div className="flex justify-between items-center">
          {/* Left side - Navigation links evenly spaced */}
          <div className="flex-1 flex items-center justify-around">
            {isAdminRoute ? (
              // Admin navigation links
              <>
                <Link to="/AdminInstitutions" className={navLinkClasses}>
                  Institutions
                </Link>
                <Link to="/AdminLeague" className={navLinkClasses}>
                  League Management
                </Link>
                <Link to="/AdminLeagueSimulation" className={navLinkClasses}>
                  League Simulation
                </Link>
                <Link to="/AdminDockerStatus" className={navLinkClasses}>
                  Docker Status
                </Link>
                <Link to="/AdminDemoUsers" className={navLinkClasses}>
                  Demo Users
                </Link>
              </>
            ) : isInstitutionRoute ? (
              // Institution navigation links
              <>
                <Link to="/InstitutionTeam" className={navLinkClasses}>
                  Team Section
                </Link>
                <Link to="/InstitutionLeague" className={navLinkClasses}>
                  League Management
                </Link>
                <Link
                  to="/InstitutionLeagueSimulation"
                  className={navLinkClasses}
                >
                  League Simulation
                </Link>
              </>
            ) : (
              // Public navigation links
              <>
                <Link to="/" className={navLinkClasses}>
                  Home
                </Link>
                <Link to="/Demo" className={navLinkClasses}>
                  Demo
                </Link>
                <Link to="/Institution" className={navLinkClasses}>
                  Institutions
                </Link>
                <Link to="/Leaderboards" className={navLinkClasses}>
                  Leaderboards
                </Link>
                <Link to="/AgentLogin" className={navLinkClasses}>
                  Player Login
                </Link>
              </>
            )}
          </div>

          {/* Right side - GitHub info and logout */}
          <div className="flex items-center">
            {/* GitHub Repo Info */}
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
                  <li>★ 12</li>
                  <li>🍴 3</li>
                </ul>
              </div>
            </a>

            {/* Logout Button based on user role */}
            {(isAdminRoute ||
              isInstitutionRoute ||
              currentUser?.role === "student") && (
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