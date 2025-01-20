import AgentGamesNavbar from './Navbar';
import AgentHome from './AgentGames/AgentHome';
import AgentLogin from './AgentGames/User/AgentLogin';
import AgentRankings from './AgentGames/Utilities/Rankings';
import AgentSubmission from './AgentGames/User/AgentSubmission';
import AgentLeagueSignUp from './AgentGames/User/LeagueSignup';
import Admin from './AgentGames/Admin/Admin';
import AdminLeague from './AgentGames/Admin/AdminLeague';
import AdminTeam from './AgentGames/Admin/AdminTeam';
import StyleGuide from './StyleGuide';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import React from 'react';
import { useDispatch } from 'react-redux';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import { toggleTooltips } from './slices/settingsSlice';
import DockerStatus from './AgentGames/Admin/DockerStatus';

function App() {
  const dispatch = useDispatch();

  const toggleState = () => {
    dispatch(toggleTooltips());
  };

  return (
    <BrowserRouter>
      <div className="App">
        <AgentGamesNavbar />
        <Routes>
          <Route path="/" element={<AgentHome />} />
          <Route path="AgentLogin" element={<AgentLogin />} />
          <Route path="AgentLeagueSignUp" element={<AgentLeagueSignUp />} />
          <Route path="AgentSubmission" element={<AgentSubmission />} />
          <Route path="Rankings" element={<AgentRankings />} />
          <Route path="Admin" element={<Admin />} />
          <Route path="AdminLeague" element={<AdminLeague />} />
          <Route path="AdminTeam" element={<AdminTeam />} />
          <Route path="StyleGuide" element={<StyleGuide />} />
          <Route path="AdminDockerStatus" element={<DockerStatus />} />
        </Routes>

        <ToastContainer
          position="top-center"
          autoClose={3000}
          hideProgressBar={false}
          newestOnTop={false}
          closeOnClick
          rtl={false}
          pauseOnFocusLoss
          draggable
          pauseOnHover
          theme="light"
        />

        <button
          onClick={toggleState}
          className="fixed bottom-4 right-4 w-10 h-10 bg-primary hover:bg-primary-hover text-white rounded-full shadow-lg flex items-center justify-center transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary-light"
          title="Toggle tooltips"
          aria-label="Toggle tooltips"
        >
          i
        </button>
      </div>
    </BrowserRouter>
  );
}

export default App;