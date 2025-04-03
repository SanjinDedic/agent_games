import AgentGamesNavbar from './Navbar';
import AgentHome from './AgentGames/AgentHome';
import AgentLogin from './AgentGames/User/AgentLogin';
import AgentRankings from "./AgentGames/Shared/Utilities/Rankings";
import AgentSubmission from './AgentGames/User/AgentSubmission';
import AgentLeagueSignUp from './AgentGames/User/LeagueSignup';
import Demo from './AgentGames/Demo';
import Institutions from './AgentGames/Institutions';
import Institution from "./AgentGames/Institution/Institution";
import InstitutionTeam from "./AgentGames/Institution/InstitutionTeam";
import InstitutionLeague from "./AgentGames/Institution/InstitutionLeague";
import Leaderboards from './AgentGames/Leaderboards';
import Admin from './AgentGames/Admin/Admin';
import AdminLeague from './AgentGames/Admin/AdminLeague';
import AdminInstitutions from "./AgentGames/Admin/AdminInstitutions";
import StyleGuide from './StyleGuide';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import React from 'react';
import { useDispatch } from 'react-redux';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import { toggleTooltips } from './slices/settingsSlice';
import DockerStatus from './AgentGames/Admin/DockerStatus';
import AdminDemoUsers from './AgentGames/Admin/AdminDemoUsers';

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
          <Route path="Demo" element={<Demo />} />
          <Route path="Institutions" element={<Institutions />} />
          <Route path="Leaderboards" element={<Leaderboards />} />
          {/* Admin Routes */}
          <Route path="Admin" element={<Admin />} />
          <Route path="AdminLeague" element={<AdminLeague />} />
          <Route path="AdminInstitutions" element={<AdminInstitutions />} />
          <Route path="AdminDemoUsers" element={<AdminDemoUsers />} />
          <Route path="AdminDockerStatus" element={<DockerStatus />} />
          {/* Institution Routes */}
          <Route path="Institution" element={<Institution />} />
          <Route path="InstitutionLeague" element={<InstitutionLeague />} />
          <Route path="InstitutionTeam" element={<InstitutionTeam />} />
          {/* Other Routes */}
          <Route path="StyleGuide" element={<StyleGuide />} />
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