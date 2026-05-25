import React from "react";
import { useNavigate } from "react-router-dom";
import LeagueAttributes from "../Shared/League/LeagueAttributes";

function InstitutionLeague() {
  const navigate = useNavigate();

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
