// src/AgentGames/Admin/AdminLeague.jsx (New Version)
import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { checkTokenExpiry } from '../../slices/authSlice';
import LeagueManagement from '../Shared/League/LeagueManagement';

/**
 * Admin-specific wrapper around the shared LeagueManagement component
 */
function AdminLeague() {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const currentUser = useSelector((state) => state.auth.currentUser);
  const isAuthenticated = useSelector((state) => state.auth.isAuthenticated);

  // Check authentication and authorization on component mount
  useEffect(() => {
    const tokenExpired = dispatch(checkTokenExpiry());
    if (!isAuthenticated || currentUser.role !== "admin" || tokenExpired) {
      navigate('/Admin');
    }
  }, [navigate, dispatch, isAuthenticated, currentUser]);

  // Handle unauthorized access
  const handleUnauthorized = () => {
    navigate('/Admin');
  };

  return (
    <LeagueManagement 
      userRole="admin"
      redirectPath="/Admin"
      onUnauthorized={handleUnauthorized}
    />
  );
}

export default AdminLeague;