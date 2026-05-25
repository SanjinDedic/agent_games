import React from "react";
import { useNavigate } from "react-router-dom";
import LeagueSimulationPage from "../Shared/League/LeagueSimulationPage";

function AdminLeagueSimulation() {
  const navigate = useNavigate();

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