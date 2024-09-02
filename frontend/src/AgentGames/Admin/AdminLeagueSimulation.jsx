import React, { useState } from 'react';
import { toast } from 'react-toastify';
import { useDispatch, useSelector } from 'react-redux';
import { addSimulationResult } from '../../slices/leaguesSlice';
import './css/adminleague.css';

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
      const response = await fetch(`${apiUrl}/run_simulation`, {
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
        toast.update(toastId, { render: data.message, type: "success", isLoading: false, autoClose: 2000 });
      } else if (data.status === "failed" || data.status === "error") {
        toast.update(toastId, { render: data.message, type: "error", isLoading: false, autoClose: 2000 });
      }
    } catch (error) {
      toast.update(toastId, { render: "Error loading results", type: "error", isLoading: false, autoClose: 2000 });
    }
  };

  return (
    <div className="admin-league-simulation">
      <div className="simulation-controls">
        <button className="run-simulation" onClick={handleSimulation}>RUN SIMULATION</button>
        <input
          type="number"
          placeholder="Number of simulations"
          className="number-input"
          value={simulationNumber}
          onChange={handleNumberChange}
          min="1"
        />
      </div>
      <div className="docker-toggle">
        <label style={{ margin: '12px 0px' }}>
          <input
            type="checkbox"
            checked={useDocker}
            onChange={handleDockerToggle}
          />
          Use Docker
        </label>
      </div>
    </div>
  );
};

export default AdminLeagueSimulation;