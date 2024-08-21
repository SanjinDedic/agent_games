import './css/adminteam.css';
import React, { useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import { useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { setTeams, addTeam, removeTeam  } from '../../slices/teamsSlice'


function AdminTeam() {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const teams = useSelector((state) => state.teams.list);
  const accessToken = useSelector((state) => state.auth.token);
  const currentUser = useSelector((state) => state.auth.currentUser);
  const isAuthenticated = useSelector((state) => state.auth.isAuthenticated);
  const [isLoading, setIsLoading] = useState(false);
  const [Team, setTeam] = useState({ name: '', password: '' });
  const [showAddTeamForm, setShowAddTeamForm] = useState(false);
  const state = useSelector((state) => state);
  

  useEffect(() => {
    if (!isAuthenticated || currentUser.role !== "admin") {
      // Redirect to the home page if not authenticated
      navigate('/Admin');
    }
    
  }, [navigate]);

  const handleChange = (e) => {
    setTeam(prev => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
  };

  useEffect(() => {
    setIsLoading(true);
    fetch(apiUrl + '/get_all_teams')
      .then(response => response.json())
      .then(data => {
        if (data.status === "success" && Array.isArray(data.data.all_teams)) {

          dispatch(setTeams(data.data.all_teams));
        } else if (data.status === "failed") {
          toast.error(data.message);
        } else if (data.detail === "Invalid token") {
          localStorage.removeItem('admin_token');
          navigate('/Admin');
        }
        setIsLoading(false);
      })
      .catch(error => {
        console.error('Error fetching options:', error);
        setIsLoading(false);
      });
  }, []);

  const handleAddTeam = () => {
    fetch(`${apiUrl}/team_create`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      },
      body: JSON.stringify({ name: Team.name, password: Team.password }),
    })
      .then(response => response.json())
      .then(data => {
        if (data.status === "success") {
          setTeam({ name: '', password: '' });
          setShowAddTeamForm(false);
          dispatch(addTeam(data.data));
          toast.success(data.message);
        } else if (data.status === "failed") {
          toast.error(data.message)
        }
      })
      .catch(error => {
        console.error('Error adding team:', error);
        toast.error(`Failed to add team`);
      });
  };

  const handleDelete = (id, name) => {
    fetch(`${apiUrl}/delete_team`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      },
      body: JSON.stringify({ name: name }),
    })
      .then(response => response.json())
      .then(data => {
        if (data.status === "success") {
          dispatch(removeTeam(id));
          toast.success(data.message);
        } else if (data.status === "failed") {
          toast.error(data.message);
        }
        else if (data.status === "error") {
          toast.error(data.message);
        }
      })
      .catch(error => {
        console.error('Error deleting team:', error);
        toast.error(`Failed to delete team`);
      });
  };

  const handleResetPassword = (name) => {
    fetch(`${apiUrl}/reset_password`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      },
      body: JSON.stringify({ name }),
    })
      .then(response => response.json())
      .then(data => {
        if (data.status === "success") {
          toast.success(data.message);
        } else if (data.status === "failed") {
          toast.error(data.message);
        }
      })
      .catch(error => {
        console.error('Error resetting password:', error);
        toast.error(`Failed to reset password for team`);
      });
  };

  const renderTable = () => {
    const rows = [];
    for (let i = 0; i < teams.length; i += 4) {
      const row = teams.slice(i, i + 4);
      rows.push(row);
    }

    return rows.map((row, rowIndex) => (
      <tr key={rowIndex}>
        {row.map((team, colIndex) => (
          <td key={colIndex}>
            <div className="table-cell">
              {team.name}
              <button className="default-button delete" onClick={() => handleDelete(team.id, team.name)}>X</button>
              <button className="default-button reset" onClick={() => handleResetPassword(team.name)}>P</button>
            </div>
          </td>
        ))}
        {row.length < 4 && Array.from({ length: 4 - row.length }).map((_, colIndex) => (
          <td key={colIndex + row.length}></td>
        ))}
      </tr>
    ));
  };
  return (

    <div className="main-container">
      <h1>TEAM SECTION</h1>
      {isLoading ? (
        <p>Loading...</p>
      ) : (
        <table border="1">
          <thead>
            <tr>
              <th>Team Name</th>
              <th>Team Name</th>
              <th>Team Name</th>
              <th>Team Name</th>
            </tr>
          </thead>
          <tbody>
            {renderTable()}
          </tbody>
        </table>
      )}
      <button onClick={() => setShowAddTeamForm(!showAddTeamForm)} className='add_button'>Add a new team to the competition</button>

      {showAddTeamForm && (
        <div className="form-group">
          <h2>Add Team</h2>
          <input
            type="text"
            name="name"
            onChange={handleChange}
            placeholder="Enter team name"
          />
          <input
            type="text"
            name="password"
            onChange={handleChange}
            placeholder="Enter team Password"
          />
          <button onClick={handleAddTeam} className='add_team_button'>Add Team</button>
        </div>
      )}
    </div>
  );
}

export default AdminTeam;
