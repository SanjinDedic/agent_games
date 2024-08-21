import '../../css/App.css';
import './css/login.css';
import React, { useState,useEffect } from 'react';
import { useNavigate} from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { login } from '../../slices/authSlice';
import { setCurrentTeam, clearTeam } from '../../slices/teamsSlice';
import UserTooltip from '../Utilities/UserTooltips';
import InstructionPopup from '../Utilities/InstructionPopup';
import { jwtDecode } from 'jwt-decode';

function AgentLogin() {
    const navigate = useNavigate();
    const dispatch = useDispatch();
    const apiUrl = useSelector((state) => state.settings.agentApiUrl);
    const currentUser = useSelector((state) => state.auth.currentUser);
    const isAuthenticated = useSelector((state) => state.auth.isAuthenticated);
 
    useEffect(() => {
      if (!isAuthenticated || currentUser.role !== "student") {
        navigate('/AgentLogin');
      }
      else if (isAuthenticated || currentUser.role === "student") {
        navigate('/AgentLeagueSignUp');
      }
    }, [navigate]);


    const [Team, setTeam] = useState({ name: '', password: ''});
    const [errorMessage, setErrorMessage] = useState('');
    const [shake, setShake] = useState(false);
    

    const handleChange = (e) =>{
      setTeam(prev => ({
        ...prev,
        [e.target.name]: e.target.value,
      }));
    };
    
    const handleLogin = async () => {
        if (!Team.name.trim() || !Team.password.trim()) {
          setShake(true);
          setTimeout(() => setShake(false), 1000);
            setErrorMessage('Please Enter all the fields');
            return;
          }
        fetch(`${apiUrl}/team_login`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name: Team.name, password: Team.password}),
          })
        .then(response => response.json())
        .then(data => {        
          if (data.status === "success") {
            const decoded = jwtDecode(data.data.access_token);
            dispatch(login({ token: data.data.access_token, name: decoded.sub, role: decoded.role }));
            dispatch(setCurrentTeam(Team.name));
            navigate("/AgentLeagueSignUp")
          } else if (data.status === "failed"){
            setErrorMessage(data.message)
          }
          
        })
        .catch(error => console.error('Error:', error));
        
      };

  return (
          <div className="login-main-container">
      <div className="login-container">
      <InstructionPopup  homescreen={true}/>
        <div className="input-group">
          <h1>Username:</h1>
          <input
            type="text"
            id="team_name"
            name="name"
            onChange={handleChange}
            className={shake ? 'shake' : ''}
          />
        </div>
        <div className="input-group">
          <h1>Password:</h1>
          <input
            type="password"
            id="team_password"
            name="password"
            onChange={handleChange}
            className={shake ? 'shake' : ''}
          />
        </div>
        <UserTooltip title={"⚠️ INFO <br />Enter your login details provided by your teacher or school and then login."} arrow disableFocusListener disableTouchListener>
        <button onClick={handleLogin} className='submit-button'>Login</button>
        </UserTooltip>
        {errorMessage && <p className="error-message">{errorMessage}</p>}
      </div>
      
      
    </div>
  );
}

export default AgentLogin;