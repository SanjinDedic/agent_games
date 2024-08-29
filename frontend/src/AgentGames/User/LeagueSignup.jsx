import './css/leaguesignup.css';
import React, { useEffect } from 'react';
import { toast } from 'react-toastify';
import { useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import moment from 'moment-timezone';
import UserTooltip from '../Utilities/UserTooltips';
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
  
  moment.tz.setDefault("Australia/Sydney");

  useEffect(() => {
    const tokenExpired = dispatch(checkTokenExpiry());
    if (!isAuthenticated || currentUser.role !== "student" || tokenExpired) {
      // Redirect to the home page if not authenticated
      navigate('/AgentLogin');
    }
  }, [navigate]);


  useEffect(() => {
    fetch(`${apiUrl}/get_all_admin_leagues`)
      .then(response => response.json())
      .then(data => {
        if (data.status === "success") {
          dispatch(setLeagues(data.data.admin_leagues));
        } else if (data.status === "failed") {
          toast.error(data.message);
        }

      })
      .catch(error => console.error('Error fetching options:', error));
  }, []);

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

    fetch(`${apiUrl}/league_assign`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      },
      body: JSON.stringify({ name: currentLeague.name }),
    })
      .then(response => response.json())
      .then(data => {
        if (data.status === "success") {
          toast.success(data.message, {
            position: "top-center"
          });
          navigate('/AgentSubmission');
        } else if (data.status === "failed") {
          toast.error(data.message, {
            position: "top-center"
          });
        }else if (data.detail === "Invalid token") {
          navigate('/AgentLogin');
        }

      })
      .catch(error => console.error('Error:', error));

  }

  return (
    <div className='parent-container'>
      
      <div className="signup-container">
      <h1>PICK A LEAGUE TO JOIN</h1>
      <div className="grid-container">
      {allLeagues.map((league) => (
        <label key={league.id} className="grid-item">
          <input
            type="checkbox"
            name={league.name}
            checked={currentLeague.name === league.name}
            onChange={handleCheckboxChange}
          />
          <div className="league-info">
            <span className="league-name">{league.name}</span>
            <span className="league-game">{league.game}</span>
          </div>
        </label>
      ))}
      </div>
        <UserTooltip title={"⚠️ INFO <br />Please Select the required or current league for code submission"} arrow disableFocusListener disableTouchListener>
        <button className='signup-button' onClick={handleSignUp}>Join League</button>
        </UserTooltip>
      </div>
    </div>
  );
}

export default AgentLeagueSignUp;