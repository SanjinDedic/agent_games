// src/AgentGames/Institution/InstitutionLeague.jsx (Updated)
import React, { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import { checkTokenExpiry } from "../../slices/authSlice";
import LeagueAttributes from "../Shared/League/LeagueAttributes";

/**
 * Institution-specific wrapper around the league attributes management component
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
    <LeagueAttributes
      userRole="institution"
      redirectPath="/Institution"
      onUnauthorized={handleUnauthorized}
    />
  );
}

export default InstitutionLeague;
