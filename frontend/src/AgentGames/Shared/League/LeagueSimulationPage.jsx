// src/AgentGames/Shared/League/LeagueSimulationPage.jsx
import React, { useEffect } from 'react';
import moment from 'moment-timezone';
import { useNavigate } from 'react-router-dom';

// Import components
import LeagueCardList from "./LeagueCardList";
import SimulationPanel from "./SimulationPanel";

// Import hooks
import useLeagueAPI from "./../hooks/useLeagueAPI";
import { useTerms } from "../terminology";

const LeagueSimulationPage = ({ userRole, redirectPath, onUnauthorized }) => {
  const T = useTerms();
  const navigate = useNavigate();

  const api = useLeagueAPI(userRole);

  moment.tz.setDefault("Australia/Sydney");

  useEffect(() => {
    api.fetchUserLeagues();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Navigate to the league management page
  const handleGoToManagement = () => {
    const path = userRole === "admin" ? "/AdminLeague" : "/InstitutionLeague";
    navigate(path);
  };

  return (
    <div className="min-h-screen bg-ui-lighter">
      <div className="max-w-[1800px] mx-auto px-6 pt-20 pb-8">
        {/* Header */}
        <div className="mb-6">
          <div className="flex justify-between items-center">
            <h1 className="text-2xl font-bold text-ui-dark mb-4">
              {`${T.League} Simulation & Results`}
            </h1>
            <button
              onClick={handleGoToManagement}
              className="px-4 py-2 bg-primary hover:bg-primary-hover text-white rounded-lg transition-colors"
            >
              {`Go to ${T.League} Management`}
            </button>
          </div>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          {/* Left Column - League Selection */}
          <div className="space-y-4">
            <div className="bg-white rounded-lg shadow-lg p-4">
              <h2 className="text-xl font-semibold text-ui-dark mb-4">
                {`Select ${T.League}`}
              </h2>
              <LeagueCardList userRole={userRole} />
            </div>
          </div>

          {/* Right Column - Simulation controls + results */}
          <div className="lg:col-span-4">
            <SimulationPanel userRole={userRole} />
          </div>
        </div>
      </div>
    </div>
  );
};

export default LeagueSimulationPage;
