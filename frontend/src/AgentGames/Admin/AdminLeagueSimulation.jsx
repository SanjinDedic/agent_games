// src/AgentGames/Admin/AdminLeagueSimulation.jsx
import React, { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import { checkTokenExpiry } from "../../slices/authSlice";
import LeagueSimulationPage from "../Shared/League/LeagueSimulationPage";

/**
 * Admin-specific wrapper around the league simulation page component
 */
function AdminLeagueSimulation() {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const currentUser = useSelector((state) => state.auth.currentUser);
  const isAuthenticated = useSelector((state) => state.auth.isAuthenticated);

  // Check authentication and authorization on component mount
  useEffect(() => {
    const tokenExpired = dispatch(checkTokenExpiry());
    if (!isAuthenticated || currentUser.role !== "admin" || tokenExpired) {
      navigate("/Admin");
    }
  }, [navigate, dispatch, isAuthenticated, currentUser]);

  // Handle unauthorized access
  const handleUnauthorized = () => {
    navigate("/Admin");
  };

  return (
    <LeagueSimulationPage
      userRole="admin"
      redirectPath="/Admin"
      onUnauthorized={handleUnauthorized}
    />
  );
}

export default AdminLeagueSimulation;