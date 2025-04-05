import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { toast } from 'react-toastify';
import { useSelector, useDispatch } from 'react-redux';
import { login } from '../../slices/authSlice';
import { setCurrentLeague, setLeagues } from '../../slices/leaguesSlice';
import { setCurrentTeam } from '../../slices/teamsSlice';
import { jwtDecode } from 'jwt-decode';

function DirectLeagueSignup() {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const { leagueToken } = useParams();
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  
  const [leagueInfo, setLeagueInfo] = useState(null);
  const [formData, setFormData] = useState({
    teamName: '',
    password: '',
    confirmPassword: ''
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  // Fetch league info on load
  useEffect(() => {
    const fetchLeagueInfo = async () => {
      try {
        const response = await fetch(`${apiUrl}/user/league-info/${leagueToken}`);
        const data = await response.json();
        
        if (data.status === 'success') {
          setLeagueInfo(data.data);
        } else {
          setError('Invalid signup link or league not found');
        }
      } catch (err) {
        console.error("Error fetching league info:", err);
        setError('Error connecting to the server');
      }
    };
    
    if (leagueToken) {
      fetchLeagueInfo();
    }
  }, [apiUrl, leagueToken]);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validation
    if (!formData.teamName || !formData.password) {
      setError('All fields are required');
      return;
    }
    
    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      return;
    }
    
    setIsLoading(true);
    
    try {
      const response = await fetch(`${apiUrl}/user/direct-league-signup`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          team_name: formData.teamName,
          password: formData.password,
          signup_token: leagueToken
        })
      });
      
      const data = await response.json();
      
      if (data.status === 'success') {
        toast.success(data.message);
        
        if (data.data && data.data.access_token) {
          // Decode token to get expiration
          const decoded = jwtDecode(data.data.access_token);
          
          // 1. Set auth state - same as AgentLogin does
          dispatch(login({
            token: data.data.access_token,
            name: formData.teamName,
            role: 'student',
            exp: decoded.exp,
            is_demo: false
          }));
          
          // 2. Set current team - same as AgentLogin does
          dispatch(setCurrentTeam(formData.teamName));
          
          // 3. Create a full league object with all necessary properties
          const fullLeagueObject = {
            id: data.data.league_id,
            name: leagueInfo.name,
            game: leagueInfo.game,
            created_date: leagueInfo.created_date,
            expiry_date: leagueInfo.expiry_date
          };
          
          // 4. First update leagues list to include our league
          // This mimics what happens in AgentLeagueSignup
          dispatch(setLeagues([fullLeagueObject]));
          
          // 5. Then set current league by name (which will find the full object in the list)
          dispatch(setCurrentLeague(leagueInfo.name));
          
          // Give Redux state time to update before navigation
          setTimeout(() => {
            navigate('/AgentSubmission');
          }, 300);
        } else {
          navigate('/AgentLogin');
        }
      } else {
        setError(data.message || 'Failed to sign up');
      }
    } catch (err) {
      console.error('Error during signup:', err);
      setError('Error connecting to the server');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen pt-16 flex flex-col items-center justify-center bg-ui-lighter">
      <div className="w-full max-w-md px-4">
        <div className="bg-white rounded-lg shadow-lg p-8">
          <h1 className="text-2xl font-bold text-ui-dark mb-4 text-center">
            Team Sign Up
          </h1>
          
          {leagueInfo ? (
            <>
              <div className="mb-6 bg-blue-100 p-4 rounded-lg">
                <h2 className="text-lg font-semibold text-blue-700">
                  Joining League: {leagueInfo.name}
                </h2>
                <p className="text-gray-700">Game: {leagueInfo.game}</p>
              </div>
              
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label htmlFor="teamName" className="block text-ui-dark mb-1">
                    Team Name
                  </label>
                  <input
                    type="text"
                    id="teamName"
                    name="teamName"
                    value={formData.teamName}
                    onChange={handleChange}
                    className="w-full p-2 border border-ui-light rounded"
                    placeholder="Choose a team name"
                  />
                </div>
                
                <div>
                  <label htmlFor="password" className="block text-ui-dark mb-1">
                    Password
                  </label>
                  <input
                    type="password"
                    id="password"
                    name="password"
                    value={formData.password}
                    onChange={handleChange}
                    className="w-full p-2 border border-ui-light rounded"
                    placeholder="Choose a password"
                  />
                </div>
                
                <div>
                  <label htmlFor="confirmPassword" className="block text-ui-dark mb-1">
                    Confirm Password
                  </label>
                  <input
                    type="password"
                    id="confirmPassword"
                    name="confirmPassword"
                    value={formData.confirmPassword}
                    onChange={handleChange}
                    className="w-full p-2 border border-ui-light rounded"
                    placeholder="Confirm your password"
                  />
                </div>
                
                {error && (
                  <div className="text-red-600">{error}</div>
                )}
                
                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors disabled:bg-gray-400"
                >
                  {isLoading ? 'Signing up...' : 'Sign Up & Join League'}
                </button>
              </form>
              
              <div className="mt-4 text-center text-gray-600">
                <p>Already have a team? <a href="/AgentLogin" className="text-blue-600">Log in</a></p>
              </div>
            </>
          ) : error ? (
            <div className="text-center text-red-600 p-4">
              <p>{error}</p>
              <p className="mt-2">
                <a href="/" className="text-blue-600">Return to home page</a>
              </p>
            </div>
          ) : (
            <div className="text-center p-4">
              <p className="text-gray-600">Loading league information...</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default DirectLeagueSignup;