import AgentGamesNavbar from './Navbar';
import AgentHome from './AgentGames/AgentHome';
import AgentLogin from './AgentGames/User/AgentLogin';
import AgentRankings from "./AgentGames/Shared/Utilities/Rankings";
import AgentSubmission from './AgentGames/User/AgentSubmission';
import TeamHome from './AgentGames/User/TeamHome';
import Tutorial from './AgentGames/User/Tutorial';
import AgentLeagueSignUp from "./AgentGames/User/LeagueSignup";
import Institutions from './AgentGames/Institutions';
import Teachers from './AgentGames/Teachers';
import InstitutionSignup from './AgentGames/InstitutionSignup';
import InstitutionInvoiceSignup from './AgentGames/InstitutionInvoiceSignup';
import Institution from "./AgentGames/Institution/Institution";
import InstitutionTeam from "./AgentGames/Institution/InstitutionTeam";
import InstitutionLeague from "./AgentGames/Institution/InstitutionLeague";
import InstitutionLeagueSimulation from "./AgentGames/Institution/InstitutionLeagueSimulation";
import InstitutionLeagueSubmissions from "./AgentGames/Institution/InstitutionLeagueSubmissions";
import InstitutionSubscription from "./AgentGames/Institution/InstitutionSubscription";
import InstitutionProgress from "./AgentGames/Institution/InstitutionProgress";
import Leaderboards from "./AgentGames/Leaderboards";
import Admin from "./AgentGames/Admin/Admin";
import AdminLeague from "./AgentGames/Admin/AdminLeague";
import AdminLeagueSimulation from "./AgentGames/Admin/AdminLeagueSimulation";
import AdminBackup from "./AgentGames/Admin/AdminBackup";
import AdminInstitutions from "./AgentGames/Admin/AdminInstitutions";
import AdminAPIKeys from "./AgentGames/Admin/AdminAPIKeys";
import AdminTutorials from "./AgentGames/Admin/AdminTutorials";
import AdminLessons from "./AgentGames/Admin/AdminLessons";
import LessonModalProvider from "./AgentGames/Shared/Lesson/LessonModalProvider";
import StyleGuide from "./StyleGuide";
import GamePreview from "./AgentGames/GamePreview";
import PublishedResults from "./AgentGames/PublishedResults";
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import React from "react";
import { ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import "./utils/toastDefaults";
import DockerStatus from "./AgentGames/Admin/DockerStatus";
import Demo from './AgentGames/Demo';
import About from './AgentGames/About';
// import AdminDemoUsers from "./AgentGames/Admin/AdminDemoUsers";
import ClassroomJoin from "./AgentGames/User/ClassroomJoin";
import SupportButton from "./AgentGames/Support/SupportButton";
import AdminUserSupport from "./AgentGames/Admin/AdminUserSupport";
import AuthProtection from "./AgentGames/Shared/Common/AuthProotection";

function App() {
  return (
    <BrowserRouter>
      <div className="App">
        <LessonModalProvider>
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
          <Route
            path="Tutorial"
            element={
              <AuthProtection requiredRole="student" redirectTo="/AgentLogin">
                <Tutorial />
              </AuthProtection>
            }
          />
          <Route path="Rankings" element={<AgentRankings />} />
          <Route path="Demo" element={<Demo />} />
          <Route path="Institutions" element={<Institutions />} />
          <Route path="Teachers" element={<Teachers />} />
          <Route path="InstitutionSignup" element={<InstitutionSignup />} />
          <Route
            path="InstitutionInvoiceSignup"
            element={<InstitutionInvoiceSignup />}
          />
          <Route path="Leaderboards" element={<Leaderboards />} />
          <Route path="About" element={<About />} />
          {/* Per-classroom/league page: log in or sign up, land in the league.
              /TeamSignup is the legacy shared-link path and opens on signup. */}
          <Route path="/join/:leagueToken" element={<ClassroomJoin />} />
          <Route
            path="/TeamSignup/:leagueToken"
            element={<ClassroomJoin defaultTab="signup" />}
          />
          {/* New Route for Published Results */}
          <Route path="/results/:publishLink" element={<PublishedResults />} />
          {/* Admin Routes */}
          <Route path="Admin" element={<Admin />} />
          <Route
            path="AdminLeague"
            element={
              <AuthProtection requiredRole="admin" redirectTo="/Admin">
                <AdminLeague />
              </AuthProtection>
            }
          />
          <Route
            path="AdminLeagueSimulation"
            element={
              <AuthProtection requiredRole="admin" redirectTo="/Admin">
                <AdminLeagueSimulation />
              </AuthProtection>
            }
          />
          <Route
            path="AdminInstitutions"
            element={
              <AuthProtection requiredRole="admin" redirectTo="/Admin">
                <AdminInstitutions />
              </AuthProtection>
            }
          />
          {/* <Route path="AdminDemoUsers" element={<AdminDemoUsers />} /> */}
          <Route
            path="AdminBackup"
            element={
              <AuthProtection requiredRole="admin" redirectTo="/Admin">
                <AdminBackup />
              </AuthProtection>
            }
          />
          <Route
            path="AdminDockerStatus"
            element={
              <AuthProtection requiredRole="admin" redirectTo="/Admin">
                <DockerStatus />
              </AuthProtection>
            }
          />
          <Route
            path="AdminAPIKeys"
            element={
              <AuthProtection requiredRole="admin" redirectTo="/Admin">
                <AdminAPIKeys />
              </AuthProtection>
            }
          />
          <Route
            path="AdminUserSupport"
            element={
              <AuthProtection requiredRole="admin" redirectTo="/Admin">
                <AdminUserSupport />
              </AuthProtection>
            }
          />
          <Route
            path="AdminTutorials"
            element={
              <AuthProtection requiredRole="admin" redirectTo="/Admin">
                <AdminTutorials />
              </AuthProtection>
            }
          />
          <Route
            path="AdminLessons"
            element={
              <AuthProtection requiredRole="admin" redirectTo="/Admin">
                <AdminLessons />
              </AuthProtection>
            }
          />
          {/* Institution Routes */}
          <Route path="Institution" element={<Institution />} />
          <Route path="Teacher" element={<Institution variant="teacher" />} />
          <Route
            path="InstitutionLeague"
            element={
              <AuthProtection requiredRole="institution" redirectTo="/Institution">
                <InstitutionLeague />
              </AuthProtection>
            }
          />
          <Route
            path="InstitutionLeagueSimulation"
            element={
              <AuthProtection requiredRole="institution" redirectTo="/Institution">
                <InstitutionLeagueSimulation />
              </AuthProtection>
            }
          />
          <Route
            path="InstitutionLeagueSubmissions/:leagueId"
            element={
              <AuthProtection requiredRole="institution" redirectTo="/Institution">
                <InstitutionLeagueSubmissions />
              </AuthProtection>
            }
          />
          <Route
            path="InstitutionTeam"
            element={
              <AuthProtection requiredRole="institution" redirectTo="/Institution">
                <InstitutionTeam />
              </AuthProtection>
            }
          />
          <Route
            path="InstitutionSubscription"
            element={
              <AuthProtection requiredRole="institution" redirectTo="/Institution">
                <InstitutionSubscription />
              </AuthProtection>
            }
          />
          <Route
            path="InstitutionProgress"
            element={
              <AuthProtection requiredRole="institution" redirectTo="/Institution">
                <InstitutionProgress />
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

        <SupportButton />

        <CreditLink />
        </LessonModalProvider>
      </div>
    </BrowserRouter>
  );
}

function CreditLink() {
  const { pathname } = useLocation();
  const hideOn = [
    /^\/AgentSubmission\b/,
    /^\/Tutorial\b/,
    /^\/InstitutionLeagueSubmissions\//,
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