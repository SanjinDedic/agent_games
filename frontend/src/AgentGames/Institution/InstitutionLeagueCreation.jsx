import React, { useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import { useSelector } from 'react-redux';

function InstitutionLeagueCreation() {
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const accessToken = useSelector((state) => state.auth.token);
  const [games, setGames] = useState([]);
  const [leagueInfo, setLeagueInfo] = useState({
    leagueName: '',
    gameName: '',
    selectedDate: null,
  });

  useEffect(() => {
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

  const handleAddLeague = () => {
    if (!leagueInfo.leagueName.trim()) {
      toast.error('Please enter the name of the league');
      return;
    }

    fetch(`${apiUrl}/institution/league-create`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      },
      body: JSON.stringify({ name: leagueInfo.leagueName, game: leagueInfo.gameName }),
    })
      .then(response => response.json())
      .then(data => {
        if (data.status === "success") {
          setLeagueInfo({ leagueName: '', gameName: games[0] || '', selectedDate: null });
          toast.success(data.message);
          // You might want to dispatch an action here to add the new league to your Redux store
        } else if (data.status === "failed") {
          toast.error(data.message);
        }
      })
      .catch(error => {
        toast.error('Failed to add league');
      });
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
          className="w-full bg-success hover:bg-success-hover text-white py-3 rounded-lg text-base font-medium transition-colors shadow-sm focus:ring-2 focus:ring-success focus:ring-offset-2"
        >
          ADD LEAGUE
        </button>
      </div>
    </div>
  );
}

export default InstitutionLeagueCreation;