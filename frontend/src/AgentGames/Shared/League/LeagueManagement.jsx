// src/AgentGames/Shared/League/LeagueManagement.jsx
import React, { useEffect } from 'react';
import { toast } from 'react-toastify';
import { useSelector, useDispatch } from 'react-redux';
import moment from 'moment-timezone';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';

// Import sub-components (to be implemented)
import LeagueTeams from './LeagueTeams';
import LeagueSimulation from './LeagueSimulation';
import LeagueCreation from './LeagueCreation';
import LeaguePublish from './LeaguePublish';
import CustomRewards from '../Common/CustomRewards';

// Import existing components that are already shared
import ResultsDisplay from '../Utilities/ResultsDisplay';
import FeedbackSelector from '../../Feedback/FeedbackSelector';

// Import Redux actions
import {
  setCurrentLeague,
  setLeagues,
  updateExpiryDate,
  setCurrentSimulation,
  setResults,
  clearResults
} from '../../../slices/leaguesSlice';

// Import the shared API hook
import useLeagueAPI from '../hooks/useLeagueAPI';

/**
 * Shared league management component used by both Admin and Institution roles
 *
 * @param {Object} props - Component props
 * @param {string} props.userRole - User role ('admin' or 'institution')
 * @param {string} props.redirectPath - Path to redirect to on unauthorized access
 * @param {Function} props.onUnauthorized - Function to call when user is unauthorized
 */
const LeagueManagement = ({ userRole, redirectPath, onUnauthorized }) => {
  const dispatch = useDispatch();
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const accessToken = useSelector((state) => state.auth.token);
  const currentLeague = useSelector((state) => state.leagues.currentLeague);
  const allLeagues = useSelector((state) => state.leagues.list);
  const allSimulations = useSelector((state) => state.leagues.currentLeagueResults);
  const currentSimulation = useSelector((state) => state.leagues.currentLeagueResultSelected);
  
  // Use the shared API hook
  const api = useLeagueAPI(userRole);

  moment.tz.setDefault("Australia/Sydney");

  useEffect(() => {
    fetchLeagues();
  }, []);

  useEffect(() => {
    if (currentLeague?.name) {
      fetchLeagueResults();
    }
  }, [currentLeague]);

  // Fetch all leagues
  const fetchLeagues = async () => {
    try {
      const response = await fetch(`${apiUrl}/user/get-all-leagues`, {
        headers: {
          'Authorization': `Bearer ${accessToken}`
        }
      });
      
      const data = await response.json();
      
      if (data.status === "success") {
        dispatch(setLeagues(data.data.leagues));
      } else if (data.status === "failed") {
        toast.error(data.message);
      } else if (data.detail === "Invalid token") {
        onUnauthorized();
      }
    } catch (error) {
      console.error('Error fetching leagues:', error);
    }
  };

  // Fetch league results
  const fetchLeagueResults = async () => {
    try {
      const response = await fetch(`${apiUrl}/institution/get-all-league-results`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
        body: JSON.stringify({ name: currentLeague.name })
      });
      
      const data = await response.json();
      
      if (data.status === "success") {
        if (data.data.results.length === 0) {
          dispatch(clearResults());
          toast.info("No results in the selected League");
        } else {
          dispatch(setResults(data.data.results));
        }
      } else if (data.status === "failed") {
        toast.error(data.message);
        dispatch(clearResults());
      } else if (data.detail === "Invalid token") {
        onUnauthorized();
      }
    } catch (error) {
      console.error('Error fetching league results:', error);
    }
  };

  // Handle league selection change
  const handleDropdownChange = (event) => {
    dispatch(setCurrentLeague(event.target.value));
  };

  // Handle simulation selection change
  const handleTableDropdownChange = (event) => {
    dispatch(setCurrentSimulation(event.target.value));
  };

  // Handle expiry date update
  const handleExpiryDateChange = async (date) => {
    const formattedDate = date.toISOString();
    
    try {
      const result = await api.updateExpiryDate(currentLeague.name, formattedDate);
      
      if (result.success) {
        dispatch(updateExpiryDate({ 
          name: currentLeague.name, 
          expiry_date: formattedDate 
        }));
      }
    } catch (error) {
      console.error('Error updating date:', error);
    }
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
                <LeagueTeams 
                  selected_league_name={currentLeague.name}
                  userRole={userRole} 
                />
              </div>
            )}
          </div>

          {/* Right Column - Controls (1/4 width) */}
          <div className="space-y-4">
            {/* Simulation Controls */}
            <LeagueSimulation 
              league={currentLeague}
              userRole={userRole}
            />

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
            <LeagueCreation userRole={userRole} />

            {/* Publish Button */}
            {currentLeague && currentSimulation && (
              <div className="bg-white rounded-lg shadow-lg p-4">
                <LeaguePublish
                  simulation_id={currentSimulation.id}
                  selected_league_name={currentLeague.name}
                  userRole={userRole}
                />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default LeagueManagement;