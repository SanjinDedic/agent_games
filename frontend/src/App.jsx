import AgentGamesNavbar from './Navbar';
import AgentHome from './AgentGames/AgentHome';
import AgentLogin from './AgentGames/User/AgentLogin';
import AgentRankings from "./AgentGames/Shared/Utilities/Rankings";
import AgentSubmission from './AgentGames/User/AgentSubmission';
import TeamHome from './AgentGames/User/TeamHome';
import AgentLeagueSignUp from "./AgentGames/User/LeagueSignup";
import OwnerLogin from "./AgentGames/Owner/OwnerLogin";
import OwnerTeams from "./AgentGames/Owner/OwnerTeams";
import OwnerHome from "./AgentGames/Owner/OwnerHome";
import ClassroomWorkspace from "./AgentGames/Owner/Classroom/ClassroomWorkspace";
import AIProviderKeys from "./AgentGames/Owner/AIProviderKeys";
import ServiceStatus from "./AgentGames/Owner/ServiceStatus";
import Leaderboards from "./AgentGames/Leaderboards";
import StyleGuide from "./StyleGuide";
import GamePreview from "./AgentGames/GamePreview";
import PublishedResults from "./AgentGames/PublishedResults";
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import React from "react";
import { ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import "./utils/toastDefaults";
import About from './AgentGames/About';
import ClassroomJoin from "./AgentGames/User/ClassroomJoin";
import TeamPasswordReset from "./AgentGames/User/TeamPasswordReset";
import AuthProtection from "./AgentGames/Shared/Common/AuthProtection";

function App() {
  return (
    <BrowserRouter>
      <div className="App">
        <AgentGamesNavbar />
        <Routes>
          <Route path="/" element={<AgentHome />} />
          <Route path="AgentLogin" element={<AgentLogin />} />
          <Route
            path="AgentLeagueSignUp"
            element={
              <AuthProtection requiredRole="student" redirectTo="/AgentLogin">
                <AgentLeagueSignUp />
              </AuthProtection>
            }
          />
          <Route
            path="TeamHome"
            element={
              <AuthProtection requiredRole="student" redirectTo="/AgentLogin">
                <TeamHome />
              </AuthProtection>
            }
          />
          <Route
            path="AgentSubmission"
            element={
              <AuthProtection requiredRole="student" redirectTo="/AgentLogin">
                <AgentSubmission />
              </AuthProtection>
            }
          />
          <Route path="Rankings" element={<AgentRankings />} />
          <Route path="Leaderboards" element={<Leaderboards />} />
          <Route path="About" element={<About />} />
          {/* Per-classroom/league page: log in or sign up, land in the league.
              /TeamSignup is the legacy shared-link path and opens on signup. */}
          <Route path="/join/:leagueToken" element={<ClassroomJoin />} />
          <Route
            path="/TeamSignup/:leagueToken"
            element={<ClassroomJoin defaultTab="signup" />}
          />
          {/* One-time password-reset link shared by the owner */}
          <Route path="/reset/:resetToken" element={<TeamPasswordReset />} />
          <Route path="/results/:publishLink" element={<PublishedResults />} />

          {/* Owner routes. /Login serves both the login form and, on an
              unclaimed deployment, the first-run setup form. */}
          <Route path="Login" element={<OwnerLogin />} />
          <Route
            path="Home"
            element={
              <AuthProtection requiredRole="owner" redirectTo="/Login">
                <OwnerHome />
              </AuthProtection>
            }
          />
          <Route
            path="Teams"
            element={
              <AuthProtection requiredRole="owner" redirectTo="/Login">
                <OwnerTeams />
              </AuthProtection>
            }
          />
          {/* Path kept as /Classroom in both site modes: routes are canonical,
              only user-visible copy switches vocabulary. */}
          <Route
            path="Classroom/:leagueId/:tab?"
            element={
              <AuthProtection requiredRole="owner" redirectTo="/Login">
                <ClassroomWorkspace />
              </AuthProtection>
            }
          />
          <Route
            path="ServiceStatus"
            element={
              <AuthProtection requiredRole="owner" redirectTo="/Login">
                <ServiceStatus />
              </AuthProtection>
            }
          />
          <Route
            path="APIKeys"
            element={
              <AuthProtection requiredRole="owner" redirectTo="/Login">
                <AIProviderKeys />
              </AuthProtection>
            }
          />

          {/* Other Routes */}
          <Route path="StyleGuide" element={<StyleGuide />} />
          <Route path="GamePreview/:gameName" element={<GamePreview />} />
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


        <CreditLink />
      </div>
    </BrowserRouter>
  );
}

function CreditLink() {
  const { pathname } = useLocation();
  const hideOn = [
    /^\/AgentSubmission\b/,
    /^\/Classroom\//,
  ];
  if (hideOn.some((re) => re.test(pathname))) return null;

  return (
    <a
      href="https://github.com/SanjinDedic"
      target="_blank"
      rel="noopener noreferrer"
      className="fixed bottom-2 left-3 text-xs text-ui/60 hover:text-ui transition-colors duration-200 z-40"
    >
      Agent Games by Sanjin Dedic
    </a>
  );
}

export default App;
