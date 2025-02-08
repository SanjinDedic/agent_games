import React, { useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import { useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { setTeams, addTeam, removeTeam } from '../../slices/teamsSlice';
import { checkTokenExpiry } from '../../slices/authSlice';


function AdminTeam() {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const teams = useSelector((state) => state.teams.list);
  const accessToken = useSelector((state) => state.auth.token);
  const currentUser = useSelector((state) => state.auth.currentUser);
  const isAuthenticated = useSelector((state) => state.auth.isAuthenticated);
  const [isLoading, setIsLoading] = useState(false);
  const [team, setTeam] = useState({ name: '', password: '' });
  const [showAddTeamForm, setShowAddTeamForm] = useState(false);

  useEffect(() => {
    const tokenExpired = dispatch(checkTokenExpiry());
    if (!isAuthenticated || currentUser.role !== "admin" || tokenExpired) {
      navigate('/Admin');
    }
  }, [navigate, dispatch, isAuthenticated, currentUser]);

  useEffect(() => {
    setIsLoading(true);
    fetch(`${apiUrl}/admin/get-all-teams`, {
      headers: {
        'Authorization': `Bearer ${accessToken}` // Add the authorization header
      }
    })
      .then(response => response.json())
      .then(data => {
        if (data.status === "success" && Array.isArray(data.data.teams)) {
          dispatch(setTeams(data.data.teams));
        } else if (data.status === "failed") {
          toast.error(data.message);
        } else if (data.detail === "Invalid token") {
          navigate('/Admin');
        }
        setIsLoading(false);
      })
      .catch(error => {
        console.error('Error fetching teams:', error);
        setIsLoading(false);
      });
  }, [apiUrl, dispatch, navigate]);

  const handleChange = (e) => {
    setTeam(prev => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
  };

  const handleAddTeam = () => {
    fetch(`${apiUrl}/admin/team-create`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      },
      body: JSON.stringify({ name: team.name, password: team.password }),
    })
      .then(response => response.json())
      .then(data => {
        if (data.status === "success") {
          setTeam({ name: '', password: '' });
          setShowAddTeamForm(false);
          dispatch(addTeam(data.data));
          toast.success(data.message);
        } else if (data.status === "failed") {
          toast.error(data.message);
        }
      })
      .catch(error => {
        console.error('Error adding team:', error);
        toast.error('Failed to add team');
      });
  };

  const handleDelete = (id, name) => {
    fetch(`${apiUrl}/admin/delete-team`, {
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
        } else if (data.status === "failed" || data.status === "error") {
          toast.error(data.message);
        }
      })
      .catch(error => {
        console.error('Error deleting team:', error);
        toast.error('Failed to delete team');
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

  const groupTeamsIntoRows = () => {
    const rows = [];
    for (let i = 0; i < teams.length; i += 4) {
      rows.push(teams.slice(i, i + 4));
    }
    return rows;
  };

  return (
    <div className="min-h-screen bg-ui-lighter pt-20 px-6 pb-8">
      <div className="max-w-[1800px] mx-auto">
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h1 className="text-2xl font-bold text-ui-dark mb-6">Team Management</h1>

          {isLoading ? (
            <div className="flex justify-center items-center h-32">
              <div className="text-lg text-ui-dark">Loading teams...</div>
            </div>
          ) : (
            <div className="space-y-6">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr>
                      {Array(4).fill(null).map((_, index) => (
                        <th key={index} className="px-4 py-3 text-left text-lg font-semibold text-ui-dark bg-ui-lighter">
                          Team Name
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {groupTeamsIntoRows().map((row, rowIndex) => (
                      <tr key={rowIndex}>
                        {row.map((team, colIndex) => (
                          <td key={colIndex} className="p-2">
                            <div className="flex items-center justify-between gap-2 bg-ui-lighter p-3 rounded-lg">
                              <span className="text-base font-medium text-ui-dark">{team.name}</span>
                              <div className="flex gap-2">
                                <button
                                  onClick={() => handleDelete(team.id, team.name)}
                                  className="p-1.5 text-xs bg-danger hover:bg-danger-hover text-white rounded"
                                  title="Delete team"
                                >
                                  X
                                </button>
                                <button
                                  onClick={() => handleResetPassword(team.name)}
                                  className="p-1.5 text-xs bg-notice-yellow hover:bg-notice-yellow/90 text-white rounded"
                                  title="Reset password"
                                >
                                  P
                                </button>
                              </div>
                            </div>
                          </td>
                        ))}
                        {row.length < 4 && Array(4 - row.length).fill(null).map((_, index) => (
                          <td key={`empty-${index}`} className="p-2"></td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="space-y-4">
                <button
                  onClick={() => setShowAddTeamForm(!showAddTeamForm)}
                  className="w-full bg-success hover:bg-success-hover text-white py-3 rounded-lg text-lg font-medium transition-colors"
                >
                  Add a new team to the competition
                </button>

                {showAddTeamForm && (
                  <div className="bg-ui-lighter p-6 rounded-lg space-y-4">
                    <h2 className="text-xl font-semibold text-ui-dark">Add Team</h2>
                    <div className="space-y-4">
                      <input
                        type="text"
                        name="name"
                        value={team.name}
                        onChange={handleChange}
                        placeholder="Enter team name"
                        className="w-full p-3 border border-ui-light rounded-lg text-base focus:ring-2 focus:ring-primary focus:border-primary"
                      />
                      <input
                        type="text"
                        name="password"
                        value={team.password}
                        onChange={handleChange}
                        placeholder="Enter team password"
                        className="w-full p-3 border border-ui-light rounded-lg text-base focus:ring-2 focus:ring-primary focus:border-primary"
                      />
                      <button
                        onClick={handleAddTeam}
                        className="w-full bg-primary hover:bg-primary-hover text-white py-3 rounded-lg text-base font-medium transition-colors"
                      >
                        Add Team
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default AdminTeam;