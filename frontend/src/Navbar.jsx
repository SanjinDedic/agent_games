import React from 'react';
import './css/Navbar.css'
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { logout } from './slices/authSlice';
import { clearTeam } from './slices/teamsSlice';
import { clearResults, clearLeagues } from './slices/leaguesSlice';

function AgentGamesNavbar() {
  const location = useLocation();
  const navigate = useNavigate();
  const dispatch = useDispatch();
  
  // Define the admin routes
  const adminRoutes = ['/AdminTeam', '/AdminLeague'];

  // Check if the current route is an admin route
  const isAdminRoute = adminRoutes.includes(location.pathname);
  const currentUserLog = useSelector((state) => state.auth.currentUser);

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

    return (
      <nav className="navbar">
        {isAdminRoute ? (
        <>
          <Link to="/AdminTeam">Team Section</Link>
          <Link to="/AdminLeague">League Section</Link>
          <div className="admin-navbar">
          <button onClick={handleLogout} className="logout-button">Logout</button>
        </div>
        </>
      ) : (
        <>
          <Link to="/">Home</Link>
          <Link to="/AgentLogin">Game Submission</Link>
          <Link to="/Rankings">Rankings</Link>
          {currentUserLog && currentUserLog.role === 'student' && (
            <button onClick={handleUserLogout} className="logout-button">Logout</button>
          )}
        </>
      )}
  </nav>
    );
  }

export default AgentGamesNavbar;