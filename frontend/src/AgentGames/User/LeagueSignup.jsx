import React, { useEffect } from 'react';
import { toast } from 'react-toastify';
import { useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import moment from 'moment-timezone';
import UserTooltip from "../Shared/Utilities/UserTooltips";
import { setCurrentLeague, setLeagues } from '../../slices/leaguesSlice';
import { checkTokenExpiry } from '../../slices/authSlice';

function AgentLeagueSignUp() {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const accessToken = useSelector((state) => state.auth.token);
  const currentUser = useSelector((state) => state.auth.currentUser);
  const isAuthenticated = useSelector((state) => state.auth.isAuthenticated);
  const currentLeague = useSelector((state) => state.leagues.currentLeague);
  const allLeagues = useSelector((state) => state.leagues.list);
  const isDemo = useSelector((state) => state.auth.currentUser?.is_demo || false);

  moment.tz.setDefault("Australia/Sydney");

  useEffect(() => {
    const tokenExpired = dispatch(checkTokenExpiry());
    if (!isAuthenticated || currentUser.role !== "student" || tokenExpired) {
      navigate('/AgentLogin');
    }
  }, [navigate, dispatch, isAuthenticated, currentUser]);

  useEffect(() => {
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
        }
      } catch (error) {
        console.error('Error fetching leagues:', error);
      }
    };

    fetchLeagues();
  }, [apiUrl, dispatch, accessToken]);

  const handleCheckboxChange = (event) => {
    dispatch(setCurrentLeague(event.target.name));
  };

  const handleSignUp = async () => {
    if (!currentLeague) {
      toast.error('League not selected', {
        position: "top-center"
      });
      return;
    }

    try {
      const response = await fetch(`${apiUrl}/user/league-assign`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
        body: JSON.stringify({ name: currentLeague.name }),
      });

      const data = await response.json();

      if (data.status === "success") {
        toast.success(data.message, {
          position: "top-center"
        });
        navigate('/AgentSubmission');
      } else if (data.status === "failed") {
        toast.error(data.message, {
          position: "top-center"
        });
      } else if (data.detail === "Invalid token") {
        navigate('/AgentLogin');
      }
    } catch (error) {
      console.error('Error:', error);
    }
  };


  const displayLeagues = isDemo
    ? allLeagues.filter(league => league.name.toLowerCase().includes('_demo'))
    : allLeagues.filter(league => !league.name.toLowerCase().includes('_demo'));



  return (
    <div className="min-h-screen pt-16 flex items-center justify-center bg-ui-lighter">
      <div className="w-full max-w-4xl mx-4">
        <div className="bg-white rounded-lg shadow-lg p-8">
          <h1 className="text-2xl font-bold text-ui-dark mb-8 text-center">
            PICK A LEAGUE TO JOIN
          </h1>

          {isDemo && (
            <div className="mb-6 bg-notice-yellowBg border border-notice-yellow rounded-lg p-4">
              <div className="flex items-center space-x-2">
                <span className="text-lg">🕒</span>
                <p className="text-ui-dark font-medium">
                  DEMO MODE - You are using the demo version of Agent Games
                </p>
              </div>
              <p className="text-ui-dark mt-2">
                Only demo leagues are displayed. Your progress will be available for the duration of your demo session.
              </p>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 bg-ui-lighter p-6 rounded-lg">
            {displayLeagues.length > 0 ? (
              displayLeagues.map((league) => (
                <label
                  key={league.id}
                  className={`
                    flex items-center p-4 rounded-lg cursor-pointer
                    ${isDemo ? 'bg-notice-orange hover:bg-notice-orange/90' : 'bg-league-blue hover:bg-league-hover'}
                    transform transition-all duration-200 hover:scale-105
                    shadow-md
                  `}
                >
                  <input
                    type="checkbox"
                    name={league.name}
                    checked={currentLeague?.name === league.name}
                    onChange={handleCheckboxChange}
                    className="w-5 h-5 mr-4 rounded border-league-text"
                  />
                  <div className="text-white">
                    <span className="block font-bold text-lg">
                      {league.name}
                    </span>
                    <span className="block text-league-text text-sm italic">
                      {league.game}
                    </span>
                  </div>
                </label>
              ))
            ) : (
              <div className="col-span-3 text-center p-4">
                <p className="text-ui-dark">No leagues available at this time.</p>
              </div>
            )}
          </div>

          <div className="mt-8">
            <UserTooltip
              title="⚠️ INFO <br />Please Select the required or current league for code submission"
              arrow
              disableFocusListener
              disableTouchListener
            >
              <button
                onClick={handleSignUp}
                className={`w-full py-3 px-4 text-lg font-medium text-white 
                         ${isDemo ? 'bg-notice-orange hover:bg-notice-orange/90' : 'bg-primary hover:bg-primary-hover'}
                         rounded-lg transition-colors duration-200
                         shadow-md hover:shadow-lg`}
              >
                Join League
              </button>
            </UserTooltip>
          </div>
        </div>
      </div>
    </div>
  );
}

export default AgentLeagueSignUp;