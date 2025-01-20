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

  const adminRoutes = ['/AdminTeam', '/AdminLeague', '/AdminDockerStatus'];
  const isAdminRoute = adminRoutes.includes(location.pathname);
  const currentUser = useSelector((state) => state.auth.currentUser);

  const handleLogout = () => {
    dispatch(logout());
    dispatch(clearLeagues());
    dispatch(clearTeam());
    dispatch(clearResults());
    navigate('/Admin');
  };

  const handleUserLogout = () => {
    dispatch(logout());
    dispatch(clearLeagues());
    dispatch(clearTeam());
    navigate('/AgentLogin');
  };

  const navSectionClasses = "flex-1 flex justify-center items-center";

  // Match the Button component's height with px-4 py-2 and keep the padding to 8px
  const navLinkClasses =
    "inline-flex items-center px-3 py-3 text-lg text-white hover:bg-white/10 transition-colors duration-200";


  return (
    <nav className="bg-[#111827] fixed top-0 w-full z-50">
      <div className="w-full mx-auto">
        <div className="flex justify-center">
          {isAdminRoute ? (
            <div className="flex w-full justify-between items-center">
              <div className={navSectionClasses}>
                <Link to="/AdminTeam" className={navLinkClasses}>
                  Team Section
                </Link>
              </div>
              <div className={navSectionClasses}>
                <Link to="/AdminLeague" className={navLinkClasses}>
                  League Section
                </Link>
              </div>
              <div className={navSectionClasses}>
                <Link to="/AdminDockerStatus" className={navLinkClasses}>
                  Docker Status
                </Link>
              </div>
              <Button
                variant="danger"
                onClick={handleLogout}
                className="mx-4"
              >
                Logout
              </Button>
            </div>
          ) : (
            <div className="flex w-full items-center">
              <div className={navSectionClasses}>
                <Link to="/" className={navLinkClasses}>
                  Home
                </Link>
              </div>
              <div className={navSectionClasses}>
                <Link to="/AgentLogin" className={navLinkClasses}>
                  Game Submission
                </Link>
              </div>
              <div className={navSectionClasses}>
                <Link to="/Rankings" className={navLinkClasses}>
                  Rankings
                </Link>
              </div>
              {currentUser && currentUser.role === 'student' && (
                <Button
                  variant="danger"
                  onClick={handleUserLogout}
                  className="mx-4"
                >
                  Logout
                </Button>
              )}
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}

export default AgentGamesNavbar;