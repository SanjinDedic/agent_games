// src/AgentGames/Shared/League/LeagueAttributes.jsx
import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

// Import shared components
import LeagueCreation from './LeagueCreation';
import LeagueCardList from "./LeagueCardList";
import LeagueDetailsPanel from './LeagueDetailsPanel';
import useLeagueAPI from '../hooks/useLeagueAPI';
import { useTerms } from '../terminology';

const LeagueAttributes = ({ userRole, redirectPath, onUnauthorized }) => {
  const T = useTerms();
  const navigate = useNavigate();

  const { fetchUserLeagues } = useLeagueAPI(userRole);

  useEffect(() => {
    fetchUserLeagues();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Navigate to the simulation page
  const handleGoToSimulation = () => {
    const path = userRole === 'admin' ? '/AdminLeagueSimulation' : '/InstitutionLeagueSimulation';
    navigate(path);
  };

  return (
    <div className="min-h-screen bg-ui-lighter">
      <div className="max-w-[1800px] mx-auto px-6 pt-20 pb-8">
        {/* Header section */}
        <div className="mb-6">
          <div className="flex justify-between items-center">
            <h1 className="text-2xl font-bold text-ui-dark mb-4">
              {`${T.League} Management`}
            </h1>
            <button
              onClick={handleGoToSimulation}
              className="px-4 py-2 bg-notice-orange hover:bg-notice-orange/90 text-white rounded-lg transition-colors"
            >
              Go to Simulation & Results
            </button>
          </div>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Left Column - League List (1/4 width) */}
          <div className="space-y-4">
            <div className="bg-white rounded-lg shadow-lg p-4">
              <h2 className="text-xl font-semibold text-ui-dark mb-4">
                {T.Leagues}
              </h2>
              <LeagueCardList userRole={userRole} />
            </div>

            {/* League Creation */}
            <LeagueCreation userRole={userRole} />
          </div>

          {/* Right Column - League Details (3/4 width) */}
          <div className="lg:col-span-3 space-y-6">
            <LeagueDetailsPanel userRole={userRole} showTeams />
          </div>
        </div>
      </div>
    </div>
  );
};

export default LeagueAttributes;
