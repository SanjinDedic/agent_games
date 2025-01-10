import React, { useState } from 'react';
import { toast } from 'react-toastify';
import { useDispatch, useSelector } from 'react-redux';
import { addSimulationResult } from '../../slices/leaguesSlice';

const AdminLeagueSimulation = ({ selected_league_name }) => {
  const dispatch = useDispatch();
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const accessToken = useSelector((state) => state.auth.token);
  const rewards = useSelector((state) => state.leagues.currentRewards);

  const [simulationNumber, setSimulationNumber] = useState(1);
  const [useDocker, setUseDocker] = useState(true);

  const handleNumberChange = (event) => {
    const value = parseInt(event.target.value, 10);
    if (value > 0) {
      setSimulationNumber(value);
    }
  };

  const handleDockerToggle = () => {
    setUseDocker(!useDocker);
  };

  const handleSimulation = async () => {
    const toastId = toast.loading("Loading results...");

    try {
      const response = await fetch(`${apiUrl}/admin/run-simulation`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
        body: JSON.stringify({
          num_simulations: simulationNumber,
          league_name: selected_league_name,
          use_docker: useDocker,
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
      } else if (data.status === "failed" || data.status === "error") {
        toast.update(toastId, {
          render: data.message,
          type: "error",
          isLoading: false,
          autoClose: 2000
        });
      }
    } catch (error) {
      toast.update(toastId, {
        render: "Error loading results",
        type: "error",
        isLoading: false,
        autoClose: 2000
      });
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-4">
      <div className="space-y-4">
        <div className="flex items-center justify-between gap-3">
          <button
            onClick={handleSimulation}
            className="flex-grow bg-notice-orange hover:bg-notice-orange/90 text-white px-6 py-3 rounded-lg font-semibold text-lg transition-colors focus:ring-2 focus:ring-notice-orange focus:ring-offset-2 outline-none"
          >
            RUN SIMULATION
          </button>
          <input
            type="number"
            value={simulationNumber}
            onChange={handleNumberChange}
            min="1"
            className="w-20 p-2 border border-ui-light rounded-lg text-lg shadow-sm focus:ring-2 focus:ring-primary focus:border-primary outline-none"
          />
        </div>

        <label className="flex items-center gap-2 text-lg text-ui-dark hover:cursor-pointer">
          <input
            type="checkbox"
            checked={useDocker}
            onChange={handleDockerToggle}
            className="w-4 h-4 rounded border-ui-light text-primary focus:ring-primary"
          />
          <span>Use Docker</span>
        </label>
      </div>
    </div>
  );
};

export default AdminLeagueSimulation;