import React from "react";
import { useNavigate } from "react-router-dom";
import LeagueSimulationPage from "../Shared/League/LeagueSimulationPage";

function InstitutionLeagueSimulation() {
  const navigate = useNavigate();

  const handleUnauthorized = () => {
    navigate("/Institution");
  };

  return (
    <LeagueSimulationPage
      userRole="institution"
      redirectPath="/Institution"
      onUnauthorized={handleUnauthorized}
    />
  );
}

export default InstitutionLeagueSimulation;