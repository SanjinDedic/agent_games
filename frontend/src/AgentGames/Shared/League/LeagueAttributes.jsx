// src/AgentGames/Shared/League/LeagueAttributes.jsx
import React, { useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import { useSelector, useDispatch } from 'react-redux';
import moment from 'moment-timezone';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import { useNavigate } from 'react-router-dom';

// Import Redux actions 
import { 
  setLeagues, 
  setCurrentLeague, 
  updateExpiryDate 
} from '../../../slices/leaguesSlice';

// Import shared components
import LeagueTeams from './LeagueTeams';
import LeagueCreation from './LeagueCreation';
import useLeagueAPI from '../hooks/useLeagueAPI';

const LeagueAttributes = ({ userRole, redirectPath, onUnauthorized }) => {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const accessToken = useSelector((state) => state.auth.token);
  const currentLeague = useSelector((state) => state.leagues.currentLeague);
  const allLeagues = useSelector((state) => state.leagues.list);
  
  const [signupLink, setSignupLink] = useState("");
  const [showSignupLink, setShowSignupLink] = useState(false);
  const [isLoadingSignupLink, setIsLoadingSignupLink] = useState(false);
  
  // Use the shared API hook
  const { fetchUserLeagues, updateExpiryDate: updateLeagueExpiry, isLoading } = useLeagueAPI(userRole);

  moment.tz.setDefault("Australia/Sydney");

  useEffect(() => {
    fetchLeagues();
  }, []);

  // Check for existing signup links when currentLeague changes
  useEffect(() => {
    if (currentLeague && currentLeague.signup_link) {
      const baseUrl = `${window.location.protocol}//${window.location.host}`;
      const signupPath = `/TeamSignup/${currentLeague.signup_link}`;
      setSignupLink(`${baseUrl}${signupPath}`);
      setShowSignupLink(true);
    } else {
      setShowSignupLink(false);
      setSignupLink("");
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

  // Generate signup link for a league
  const generateSignupLink = async (leagueId, leagueName) => {
    if (!leagueId) return;
    
    setIsLoadingSignupLink(true);
    try {
      const response = await fetch(`${apiUrl}/institution/generate-signup-link`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
        body: JSON.stringify({ league_id: leagueId }),
      });
      
      const data = await response.json();
      
      if (data.status === "success" && data.data?.signup_token) {
        const baseUrl = `${window.location.protocol}//${window.location.host}`;
        const signupPath = `/TeamSignup/${data.data.signup_token}`;
        const fullUrl = `${baseUrl}${signupPath}`;
        
        setSignupLink(fullUrl);
        setShowSignupLink(true);
        
        toast.success(`Signup link generated for ${leagueName}`);
      } else {
        toast.error(data.message || 'Failed to generate signup link');
      }
    } catch (error) {
      console.error('Error generating signup link:', error);
      toast.error('Network error while generating signup link');
    } finally {
      setIsLoadingSignupLink(false);
    }
  };

  // Handle league selection change
  const handleDropdownChange = (event) => {
    dispatch(setCurrentLeague(event.target.value));
    setShowSignupLink(false);
  };

  // Handle expiry date update
  const handleExpiryDateChange = async (date) => {
    const formattedDate = date.toISOString();
    
    try {
      const result = await updateLeagueExpiry(currentLeague.name, formattedDate);
      
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

  // Navigate to the simulation page
  const handleGoToSimulation = () => {
    const path = userRole === 'admin' ? '/AdminLeagueSimulation' : '/InstitutionLeagueSimulation';
    navigate(path);
  };
  
  // Copy signup link to clipboard
  const copySignupLink = () => {
    navigator.clipboard.writeText(signupLink);
    toast.success("Signup link copied to clipboard!");
  };

  return (
    <div className="min-h-screen bg-ui-lighter">
      <div className="max-w-[1800px] mx-auto px-6 pt-20 pb-8">
        {/* Header and League Selection */}
        <div className="mb-6">
          <div className="flex justify-between items-center">
            <h1 className="text-2xl font-bold text-ui-dark mb-4">League Management</h1>
            <button 
              onClick={handleGoToSimulation}
              className="px-4 py-2 bg-notice-orange hover:bg-notice-orange/90 text-white rounded-lg transition-colors"
            >
              Go to Simulation & Results
            </button>
          </div>
          
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
            {/* League Attributes Card */}
            {currentLeague && (
              <div className="bg-white rounded-lg shadow-lg p-6">
                <h2 className="text-xl font-semibold text-ui-dark mb-4">League Details</h2>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                  <div>
                    <span className="block text-ui">League Name:</span>
                    <span className="block text-lg font-medium text-ui-dark">{currentLeague.name}</span>
                  </div>
                  
                  <div>
                    <span className="block text-ui">Game Type:</span>
                    <span className="block text-lg font-medium text-ui-dark">{currentLeague.game}</span>
                  </div>
                  
                  <div>
                    <span className="block text-ui">Created Date:</span>
                    <span className="block text-lg font-medium text-ui-dark">
                      {moment(currentLeague.created_date).format('MMMM D, YYYY')}
                    </span>
                  </div>
                  
                  <div>
                    <span className="block text-ui">Status:</span>
                    <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${
                      moment().isBefore(moment(currentLeague.expiry_date)) 
                        ? 'bg-success-light text-success' 
                        : 'bg-danger-light text-danger'
                    }`}>
                      {moment().isBefore(moment(currentLeague.expiry_date)) ? 'Active' : 'Expired'}
                    </span>
                  </div>
                </div>
                
                {/* League Expiry Date Editor */}
                <div className="mb-6">
                  <h3 className="text-lg font-medium text-ui-dark mb-2">League Expiry</h3>
                  <div className="flex items-center gap-2">
                    <DatePicker
                      selected={new Date(currentLeague.expiry_date)}
                      onChange={handleExpiryDateChange}
                      showTimeSelect
                      dateFormat="MMMM d, yyyy h:mm aa"
                      className="p-2 border border-ui-light rounded w-64"
                    />
                    <span className="text-ui">
                      {moment(currentLeague.expiry_date).fromNow()}
                    </span>
                  </div>
                </div>
                
                {/* League Signup Link */}
                <div className="mb-6">
                  <h3 className="text-lg font-medium text-ui-dark mb-2">Signup Link</h3>
                  
                  {showSignupLink ? (
                    <div className="p-4 bg-success-light rounded-lg">
                      <div className="flex items-center">
                        <input
                          type="text"
                          value={signupLink}
                          readOnly
                          className="flex-1 p-2 border border-ui-light rounded-lg text-sm bg-white"
                        />
                        <button
                          onClick={copySignupLink}
                          className="ml-2 p-2 bg-primary hover:bg-primary-hover text-white rounded-lg"
                          title="Copy to clipboard"
                        >
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            className="h-5 w-5"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                            />
                          </svg>
                        </button>
                      </div>
                      <p className="mt-2 text-sm text-ui-dark">
                        Share this link for teams to sign up directly to this league.
                      </p>
                    </div>
                  ) : (
                    <button
                      onClick={() => generateSignupLink(currentLeague.id, currentLeague.name)}
                      disabled={isLoadingSignupLink}
                      className="px-4 py-2 bg-primary hover:bg-primary-hover text-white rounded-lg transition-colors disabled:bg-ui-light disabled:cursor-not-allowed"
                    >
                      {isLoadingSignupLink ? 'Generating...' : 'Generate Signup Link'}
                    </button>
                  )}
                </div>
                
                {/* Teams Grid */}
                <LeagueTeams 
                  selected_league_name={currentLeague.name}
                  userRole={userRole} 
                />
              </div>
            )}
          </div>

          {/* Right Column - Controls (1/4 width) */}
          <div className="space-y-4">
            {/* League Creation */}
            <LeagueCreation userRole={userRole} />
          </div>
        </div>
      </div>
    </div>
  );
};

export default LeagueAttributes;