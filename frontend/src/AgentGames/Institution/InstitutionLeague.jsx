// src/AgentGames/Institution/InstitutionLeague.jsx (New Version)
import React, { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import { checkTokenExpiry } from "../../slices/authSlice";
import LeagueManagement from "../Shared/League/LeagueManagement";

/**
 * Institution-specific wrapper around the shared LeagueManagement component
 */
function InstitutionLeague() {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const currentUser = useSelector((state) => state.auth.currentUser);
  const isAuthenticated = useSelector((state) => state.auth.isAuthenticated);

  // Check authentication and authorization on component mount
  useEffect(() => {
    const tokenExpired = dispatch(checkTokenExpiry());
    if (
      !isAuthenticated ||
      currentUser.role !== "institution" ||
      tokenExpired
    ) {
      navigate("/Institution");
    }
  }, [navigate, dispatch, isAuthenticated, currentUser]);

  // Handle unauthorized access
  const handleUnauthorized = () => {
    navigate("/Institution");
  };

  return (
    <LeagueManagement
      userRole="institution"
      redirectPath="/Institution"
      onUnauthorized={handleUnauthorized}
    />
  );
}

export default InstitutionLeague;
