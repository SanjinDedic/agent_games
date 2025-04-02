import React, { useState } from 'react';
import { toast } from 'react-toastify';
import { useDispatch, useSelector } from 'react-redux';
import { addSimulationResult } from '../../slices/leaguesSlice';

const InstitutionLeagueSimulation = ({ league }) => {
  const dispatch = useDispatch();
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const accessToken = useSelector((state) => state.auth.token);
  const rewards = useSelector((state) => state.leagues.currentRewards);

  const [simulationNumber, setSimulationNumber] = useState(1);
  const [isLoading, setIsLoading] = useState(false);

  // Input validation
  const handleNumberChange = (event) => {
    const value = parseInt(event.target.value, 10);
    if (value > 0 && value <= 10000) { // Added upper limit
      setSimulationNumber(value);
    }
  };

  const handleSimulation = async () => {
    if (!league?.id) {
      toast.error('Please select a valid league first');
      return;
    }

    setIsLoading(true);
    const toastId = toast.loading("Running simulation...");

    try {
      const response = await fetch(`${apiUrl}/institution/run-simulation`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
        body: JSON.stringify({
          num_simulations: simulationNumber,
          league_id: league.id,
          league_name: league.name, // Keep for backwards compatibility if needed
          game: league.game,
          custom_rewards: rewards,
        }),
      });

      const data = await response.json();

      if (data.status === "success") {
        dispatch(addSimulationResult(data.data));
        toast.update(toastId, {
          render: data.message,
          type: "success",
          isLoading: false,
          autoClose: 2000
        });
      } else {
        toast.update(toastId, {
          render: data.message || 'Failed to run simulation',
          type: "error",
          isLoading: false,
          autoClose: 2000
        });
      }
    } catch (error) {
      console.error('Simulation error:', error);
      toast.update(toastId, {
        render: "Error running simulation",
        type: "error",
        isLoading: false,
        autoClose: 2000
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-4">
      <div className="space-y-4">
        <div className="flex items-center justify-between gap-3">
          <button
            onClick={handleSimulation}
            disabled={isLoading || !league?.id}
            className={`
              flex-grow px-6 py-3 rounded-lg font-semibold text-lg transition-colors
              focus:ring-2 focus:ring-offset-2 outline-none
              ${isLoading
                ? 'bg-ui-light text-ui cursor-not-allowed'
                : 'bg-notice-orange hover:bg-notice-orange/90 text-white'}
            `}
          >
            {isLoading ? 'RUNNING...' : 'RUN SIMULATION'}
          </button>

          <input
            type="number"
            value={simulationNumber}
            onChange={handleNumberChange}
            min="1"
            max="10000"
            disabled={isLoading}
            className="w-24 p-2 border border-ui-light rounded-lg text-lg shadow-sm 
                     focus:ring-2 focus:ring-primary focus:border-primary outline-none
                     disabled:bg-ui-light disabled:cursor-not-allowed"
          />
        </div>

        {league && (
          <div className="text-sm text-ui">
            Selected League: {league.name} ({league.game})
          </div>
        )}
      </div>
    </div>
  );
};

export default InstitutionLeagueSimulation;