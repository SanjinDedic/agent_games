import './css/App.css';
import AgentGamesNavbar from './Navbar';
import AgentHome from './AgentGames/AgentHome';
import AgentLogin from './AgentGames/User/AgentLogin';
import AgentRankings from './AgentGames/Utilities/Rankings';
import AgentSubmission from './AgentGames/User/AgentSubmission';
import AgentLeagueSignUp from './AgentGames/User/LeagueSignup';
import Admin from './AgentGames/Admin/Admin';
import AdminLeague from './AgentGames/Admin/AdminLeague';
import AdminTeam from './AgentGames/Admin/AdminTeam';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import React from 'react';
import { useDispatch } from 'react-redux';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import { toggleTooltips } from './slices/settingsSlice';


function App() {

  const dispatch = useDispatch();

  const toggleState = () => {
    dispatch(toggleTooltips())
  };

  return (
    <BrowserRouter>
      <div className="App">
      <AgentGamesNavbar/>
        <Routes>
          <Route path="/" element={<AgentHome/>} />
          <Route path="AgentLogin" element={<AgentLogin/>} />
          <Route path="AgentLeagueSignUp" element={<AgentLeagueSignUp/>} />
          <Route path="AgentSubmission" element={<AgentSubmission/>} />
          
          <Route path="Rankings" element={<AgentRankings />} />
          
          <Route path="Admin" element={<Admin/>} />
          <Route path="AdminLeague" element={<AdminLeague/>} />
          <Route path="AdminTeam" element={<AdminTeam/>} />
        </Routes>
        <ToastContainer  className="toast-container" />
        <button className='icon-button' onClick={toggleState}>I</button>
      </div>
    </BrowserRouter>
    
  );
}

export default App;
