import React, { useEffect } from 'react';
import { toast } from 'react-toastify';
import { useNavigate } from 'react-router-dom';
import ResultsDisplay from '../Utilities/ResultsDisplay';
import FeedbackSelector from '../Utilities/FeedbackSelector';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import moment from 'moment-timezone';
import AdminLeagueCreation from './AdminLeagueCreation';
import AdminLeagueTeams from './AdminLeagueTeams';
import AdminLeagueSimulation from './AdminLeagueSimulation';
import AdminLeaguePublish from './AdminLeaguePublish';
import CustomRewards from './CustomRewards';
import { useDispatch, useSelector } from 'react-redux';
import { setCurrentLeague, setLeagues, updateExpiryDate, setCurrentSimulation, setResults, clearResults } from '../../slices/leaguesSlice';
import { checkTokenExpiry } from '../../slices/authSlice';

function AdminLeague() {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const currentLeague = useSelector((state) => state.leagues.currentLeague);
  const allLeagues = useSelector((state) => state.leagues.list);
  const allSimulations = useSelector((state) => state.leagues.currentLeagueResults);
  const currentSimulation = useSelector((state) => state.leagues.currentLeagueResultSelected);
  const accessToken = useSelector((state) => state.auth.token);
  const currentUser = useSelector((state) => state.auth.currentUser);
  const isAuthenticated = useSelector((state) => state.auth.isAuthenticated);

  moment.tz.setDefault("Australia/Sydney");

  useEffect(() => {
    const tokenExpired = dispatch(checkTokenExpiry());
    if (!isAuthenticated || currentUser.role !== "admin" || tokenExpired) {
      navigate('/Admin');
    }
  }, [navigate]);

  useEffect(() => {
    fetchAdminLeagues();
  }, []);

  const fetchAdminLeagues = () => {
    fetch(`${apiUrl}/user/get-all-leagues`, {
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    })
      .then(response => response.json())
      .then(data => {
        if (data.status === "success") {
          dispatch(setLeagues(data.data.leagues));
        } else if (data.status === "failed") {
          toast.error(data.message)
        } else if (data.detail === "Invalid token") {
          navigate('/Admin');
        }
      })
      .catch(error => console.error('Error fetching options:', error));
  }

  useEffect(() => {
    if (currentLeague?.name) {
      fetch(`${apiUrl}/admin/get-all-league-results`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
        body: JSON.stringify({ name: currentLeague.name })
      })
        .then(response => response.json())
        .then(data => {
          if (data.status === "success") {
            if (data.data.results.length == 0) {
              dispatch(clearResults());
              toast.error("No results in the selected League")
            } else {
              dispatch(setResults(data.data.results));
            }
          } else if (data.status === "failed") {
            toast.error(data.message);
            dispatch(clearResults());
          } else if (data.detail === "Invalid token") {
            navigate('/Admin');
          }
        })
        .catch(error => console.error('Error fetching league results:', error));
    }
  }, [currentLeague]);

  const handleDropdownChange = (event) => {
    dispatch(setCurrentLeague(event.target.value));
  };

  const handletableDropdownChange = (event) => {
    dispatch(setCurrentSimulation(event.target.value));
  };

  const handleExpiryDateChange = (date) => {
    const formattedDate = date.toISOString();
    fetch(`${apiUrl}/admin/update-expiry-date`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      },
      body: JSON.stringify({ date: formattedDate, league: currentLeague.name }),
    })
      .then(response => response.json())
      .then(data => {
        if (data.status === "success") {
          dispatch(updateExpiryDate({ name: currentLeague.name, expiry_date: formattedDate }));
          toast.success(data.message);
        } else if (data.status === "failed") {
          toast.error(data.message)
        }
      })
      .catch(error => {
        console.error('Error updating date:', error);
      });
  };

  return (
    <div className="min-h-screen bg-ui-lighter">
      <div className="max-w-[1800px] mx-auto px-6 pt-20 pb-8">
        {/* Header and League Selection */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-ui-dark mb-4">League Section</h1>
          {currentLeague && (
            <select
              onChange={handleDropdownChange}
              value={currentLeague.name}
              className="w-full p-3 border border-ui-light rounded-lg bg-white text-ui-dark text-lg shadow-sm focus:ring-2 focus:ring-primary focus:border-primary transition-all"
            >
              {allLeagues.map((league, index) => (
                <option
                  key={index}
                  value={league.name}
                  className={moment().isBefore(moment(league.expiry_date)) ? 'text-success' : 'text-danger'}
                >
                  {moment().isBefore(moment(league.expiry_date)) ? '🟢' : '🔴'} {league.name} ({league.game})
                </option>
              ))}
            </select>
          )}
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Left Column - League Data (3/4 width) */}
          <div className="lg:col-span-3 space-y-6">
            {/* Results Selection */}
            <div className="bg-white rounded-lg shadow-lg p-6">
              {allSimulations && (
                <select
                  onChange={handletableDropdownChange}
                  className="w-full p-3 mb-4 border border-ui-light rounded-lg bg-white text-ui-dark text-lg shadow-sm focus:ring-2 focus:ring-primary focus:border-primary transition-all"
                >
                  {allSimulations.map((option, index) => (
                    <option key={index} value={option.timestamp}>
                      {new Date(option.timestamp).toLocaleString()}
                    </option>
                  ))}
                </select>
              )}

              {/* Results Display */}
              {currentSimulation && (
                <>
                  <ResultsDisplay
                    data={currentSimulation}
                    highlight={false}
                    data_message={currentSimulation.message}
                    tablevisible={!currentSimulation.feedback}
                  />
                  {currentSimulation.feedback && (
                    <div className="mt-6">
                      <FeedbackSelector feedback={currentSimulation.feedback} />
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Teams Grid */}
            {currentLeague && (
              <div className="w-full bg-white rounded-lg shadow-lg p-6">
                <AdminLeagueTeams selected_league_name={currentLeague.name} />
              </div>
            )}
          </div>

          {/* Right Column - Controls (1/4 width) */}
          <div className="space-y-4">
            {/* Simulation Controls */}
            <AdminLeagueSimulation league={currentLeague} />

            {/* Custom Rewards */}
            <CustomRewards />

            {/* Expiry Date */}
            <div className="bg-white rounded-lg shadow-lg p-4">
              <h3 className="font-medium text-lg text-ui-dark mb-2">Expiry Date</h3>
              {currentLeague && (
                <DatePicker
                  selected={new Date(currentLeague.expiry_date)}
                  onChange={handleExpiryDateChange}
                  dateFormat="dd/MM/yyyy"
                  className="w-full p-3 border border-ui-light rounded-lg text-base shadow-sm focus:ring-2 focus:ring-primary focus:border-primary"
                />
              )}
            </div>

            {/* League Creation */}
            <AdminLeagueCreation />

            {/* Publish Button */}
            {currentLeague && currentSimulation && (
              <div className="bg-white rounded-lg shadow-lg p-4">
                <AdminLeaguePublish
                  simulation_id={currentSimulation.id}
                  selected_league_name={currentLeague.name}
                />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default AdminLeague;