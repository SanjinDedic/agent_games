import React from "react";
import { useNavigate } from "react-router-dom";
import LeagueAttributes from "../Shared/League/LeagueAttributes";

function AdminLeague() {
  const navigate = useNavigate();

  const handleUnauthorized = () => {
    navigate("/Admin");
  };

  return (
    <LeagueAttributes
      userRole="admin"
      redirectPath="/Admin"
      onUnauthorized={handleUnauthorized}
    />
  );
}

export default AdminLeague;
