// src/AgentGames/Shared/League/LeagueCreation.jsx
import React, { useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import { useSelector } from 'react-redux';
import useLeagueAPI from '../hooks/useLeagueAPI';

/**
 * Shared component for creating a new league
 * 
 * @param {Object} props - Component props
 * @param {string} props.userRole - User role ('admin' or 'institution')
 */
const LeagueCreation = ({ userRole }) => {
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const [games, setGames] = useState([]);
  const [leagueInfo, setLeagueInfo] = useState({
    leagueName: '',
    gameName: '',
    selectedDate: null,
  });
  
  // Use the shared API hook
  const { createLeague, isLoading } = useLeagueAPI(userRole);

  useEffect(() => {
    // Fetch available games
    fetch(`${apiUrl}/user/get-available-games`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    })
      .then(response => response.json())
      .then(data => {
        if (data.status === "success") {
          setGames(data.data.games);
          setLeagueInfo(prev => ({
            ...prev,
            gameName: data.data.games[0]
          }));
        } else if (data.status === "failed") {
          toast.error(data.message);
        }
      })
      .catch(error => {
        console.error('Error fetching games:', error);
        toast.error('Failed to fetch available games');
      });
  }, [apiUrl]);

  const handleGameDropdownChange = (event) => {
    setLeagueInfo(prev => ({
      ...prev,
      gameName: event.target.value
    }));
  };

  const handleChange = (event) => {
    setLeagueInfo(prev => ({
      ...prev,
      [event.target.name]: event.target.value,
    }));
  };

  const handleDateChange = (date) => {
    setLeagueInfo(prev => ({
      ...prev,
      selectedDate: date
    }));
  };

  const handleAddLeague = async () => {
    if (!leagueInfo.leagueName.trim()) {
      toast.error('Please enter the name of the league');
      return;
    }

    const leagueData = {
      name: leagueInfo.leagueName,
      game: leagueInfo.gameName
    };
    
    // If expiry date is provided, add it to the request
    if (leagueInfo.selectedDate) {
      leagueData.expiry_date = leagueInfo.selectedDate.toISOString();
    }
    
    const result = await createLeague(leagueData);
    
    if (result.success) {
      // Reset form after successful creation
      setLeagueInfo({
        leagueName: '',
        gameName: games[0] || '',
        selectedDate: null
      });
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-4">
      <h3 className="font-medium text-lg text-ui-dark mb-4">Create New League</h3>
      <div className="space-y-3">
        <input
          type="text"
          name="leagueName"
          value={leagueInfo.leagueName}
          onChange={handleChange}
          placeholder="Enter League name"
          className="w-full p-3 border border-ui-light rounded-lg text-base shadow-sm focus:ring-2 focus:ring-primary focus:border-primary"
        />

        {games && games.length > 0 && (
          <select
            onChange={handleGameDropdownChange}
            value={leagueInfo.gameName}
            className="w-full p-3 border border-ui-light rounded-lg text-base bg-white shadow-sm focus:ring-2 focus:ring-primary focus:border-primary"
          >
            {games.map((name, index) => (
              <option key={index} value={name}>
                {name}
              </option>
            ))}
          </select>
        )}

        <DatePicker
          selected={leagueInfo.selectedDate}
          onChange={handleDateChange}
          dateFormat="dd/MM/yyyy"
          placeholderText="Select expiry date (optional)"
          className="w-full p-3 border border-ui-light rounded-lg text-base shadow-sm focus:ring-2 focus:ring-primary focus:border-primary"
        />

        <button
          onClick={handleAddLeague}
          disabled={isLoading}
          className="w-full bg-success hover:bg-success-hover text-white py-3 rounded-lg text-base font-medium transition-colors shadow-sm focus:ring-2 focus:ring-success focus:ring-offset-2 disabled:bg-ui-light disabled:cursor-not-allowed"
        >
          {isLoading ? 'CREATING...' : 'ADD LEAGUE'}
        </button>
      </div>
    </div>
  );
};

export default LeagueCreation;