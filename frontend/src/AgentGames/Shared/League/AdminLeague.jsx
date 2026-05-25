import React from 'react';
import { useNavigate } from 'react-router-dom';
import LeagueManagement from '../Shared/League/LeagueManagement';

function AdminLeague() {
  const navigate = useNavigate();

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