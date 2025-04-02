import React, { useEffect } from 'react';
import { toast } from 'react-toastify';
import { useNavigate } from 'react-router-dom';
import ResultsDisplay from '../Utilities/ResultsDisplay';
import FeedbackSelector from '../Feedback/FeedbackSelector';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import moment from 'moment-timezone';
import InstitutionLeagueCreation from './InstitutionLeagueCreation';
import InstitutionLeagueTeams from './InstitutionLeagueTeams';
import InstitutionLeagueSimulation from './InstitutionLeagueSimulation';
import InstitutionLeaguePublish from './InstitutionLeaguePublish';
import CustomRewards from './CustomRewards';
import { useDispatch, useSelector } from 'react-redux';
import { setCurrentLeague, setLeagues, updateExpiryDate, setCurrentSimulation, setResults, clearResults } from '../../slices/leaguesSlice';
import { checkTokenExpiry } from '../../slices/authSlice';

function InstitutionLeague() {
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
    if (!isAuthenticated || currentUser.role !== "institution" || tokenExpired) {
      navigate('/Institution');
    }
  }, [navigate, dispatch, isAuthenticated, currentUser]);

  useEffect(() => {
    fetchInstitutionLeagues();
  }, []);

  const fetchInstitutionLeagues = () => {
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
          navigate('/Institution');
        }
      })
      .catch(error => console.error('Error fetching leagues:', error));
  }

  useEffect(() => {
    if (currentLeague?.name) {
      fetch(`${apiUrl}/institution/get-all-league-results`, {
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
            if (data.data.results.length === 0) {
              dispatch(clearResults());
              toast.info("No results in the selected League")
            } else {
              dispatch(setResults(data.data.results));
            }
          } else if (data.status === "failed") {
            toast.error(data.message);
            dispatch(clearResults());
          } else if (data.detail === "Invalid token") {
            navigate('/Institution');
          }
        })
        .catch(error => console.error('Error fetching league results:', error));
    }
  }, [currentLeague, accessToken, apiUrl, dispatch, navigate]);

  const handleDropdownChange = (event) => {
    dispatch(setCurrentLeague(event.target.value));
  };

  const handleTableDropdownChange = (event) => {
    dispatch(setCurrentSimulation(event.target.value));
  };

  const handleExpiryDateChange = (date) => {
    const formattedDate = date.toISOString();
    fetch(`${apiUrl}/institution/update-expiry-date`, {
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
        toast.error('Failed to update expiry date');
      });
  };

  return (
    <div className="min-h-screen bg-ui-lighter">
      <div className="max-w-[1800px] mx-auto px-6 pt-20 pb-8">
        {/* Header and League Selection */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-ui-dark mb-4">League Management</h1>
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
              {allSimulations && allSimulations.length > 0 && (
                <select
                  onChange={handleTableDropdownChange}
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
                <InstitutionLeagueTeams selected_league_name={currentLeague.name} />
              </div>
            )}
          </div>

          {/* Right Column - Controls (1/4 width) */}
          <div className="space-y-4">
            {/* Simulation Controls */}
            <InstitutionLeagueSimulation league={currentLeague} />

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
            <InstitutionLeagueCreation />

            {/* Publish Button */}
            {currentLeague && currentSimulation && (
              <div className="bg-white rounded-lg shadow-lg p-4">
                <InstitutionLeaguePublish
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

export default InstitutionLeague;