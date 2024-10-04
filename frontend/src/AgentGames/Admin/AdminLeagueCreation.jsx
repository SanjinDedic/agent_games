import './css/adminleague.css';
import React, { useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import { useSelector } from 'react-redux';



function AdminLeagueCreation() {
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const accessToken = useSelector((state) => state.auth.token);
  const [games, setGames] = useState([]);
  const [leagueInfo, setleagueInfo] = useState({
    leagueName: '',
    gameName: '',
    selectedDate: null,
  });

  useEffect(() => {
    fetch(`${apiUrl}/get_available_games`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    })
      .then(response => response.json())
      .then(data => {
        if (data.status === "success") {
          setGames(data.data.games);
          setleagueInfo(prev => ({
            ...prev,
            gameName: data.data.games[0]
          }));
        } else if (data.status === "failed") {
          toast.error(data.message);
        }
      })
      .catch(error => {
  
        toast.error(`Failed to add League`);
      });

  }, []);

  const handleGameDropdownChange = (event) => {
    setleagueInfo(prev => ({
      ...prev,
      gameName: event.target.value
    }));
  };

  const handleChange = (event) => {
    setleagueInfo(prev => ({
      ...prev,
      [event.target.name]: event.target.value,
    }));
  };

  const handleDateChange = (date) => {
    setleagueInfo(prev => ({
      ...prev,
      selectedDate: date
    }));
  };

  

  const handleAddLeague = () => {
    if (!leagueInfo.leagueName.trim()) {
      toast.error(`Please Enter the name of the league`);
      return;
    }
    
    fetch(`${apiUrl}/league_create`, {
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
          setleagueInfo({ leagueName: '', gameName: '', selectedDate: null });
          toast.success(data.message);
        } else if (data.status === "failed") {
          toast.error(data.message);
        }
      })
      .catch(error => {

        toast.error(`Failed to add League`);
      });

  };
    
    
  
    
    
  return (
    <>
      <div className='league-creation-container'>
        <input type="text"
          name="leagueName"
          className="league-creation-input"
          onChange={handleChange}
          placeholder="Enter League name"
          value={leagueInfo.leagueName || ''}></input>

        {games &&
        
        <select onChange={handleGameDropdownChange} className='game-select'>
          {games.map((name, index) => (
            <option key={index} value={name} >
              {name}
            </option>
          ))}
        </select>
        }

        <DatePicker
          selected={leagueInfo.selectedDate}
          onChange={handleDateChange}
          dateFormat="dd/MM/yyyy"
          placeholderText="Select a date"
          id="date-picker"
        />
        <button onClick={handleAddLeague} className='add-league-button'>ADD LEAGUE</button>

      </div>
    </>
  );
}

export default AdminLeagueCreation;