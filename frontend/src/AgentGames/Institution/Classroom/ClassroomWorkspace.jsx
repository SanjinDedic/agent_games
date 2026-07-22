import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { toast } from 'react-toastify';
import moment from 'moment-timezone';

import { setCurrentLeagueById } from '../../../slices/leaguesSlice';
import useLeagueAPI from '../../Shared/hooks/useLeagueAPI';
import { useTerms } from '../../Shared/terminology';
import SimulationPanel from '../../Shared/League/SimulationPanel';
import LeagueDetailsPanel from '../../Shared/League/LeagueDetailsPanel';
import StudentsTab from './StudentsTab';
import TutorialMatrixTab from './TutorialMatrixTab';
import SubmissionsTab from './SubmissionsTab';

const TAB_KEYS = ['students', 'tutorials', 'submissions', 'simulation', 'settings'];

/**
 * The classroom workspace: everything about one classroom/league behind
 * tabs. URL-driven (/Classroom/:leagueId/:tab?) so any tab is linkable.
 */
function ClassroomWorkspace() {
  const T = useTerms();
  const { leagueId, tab } = useParams();
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const leagues = useSelector((state) => state.leagues.list);
  const { fetchUserLeagues } = useLeagueAPI('institution');
  const [leaguesLoaded, setLeaguesLoaded] = useState(false);

  const numericId = Number(leagueId);
  const activeTab = TAB_KEYS.includes(tab) ? tab : 'students';
  const league = leagues.find((l) => l.id === numericId);

  useEffect(() => {
    let active = true;
    (async () => {
      await fetchUserLeagues();
      if (active) setLeaguesLoaded(true);
    })();
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Keep Redux selection in sync with the URL so the shared Simulation and
  // Settings panels (which read currentLeague) target this classroom.
  useEffect(() => {
    if (league) {
      dispatch(setCurrentLeagueById(numericId));
    }
  }, [league, numericId, dispatch]);

  useEffect(() => {
    if (leaguesLoaded && !league) {
      toast.error(`${T.League} not found`);
      navigate('/InstitutionHome');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [leaguesLoaded, league]);

  if (!league) {
    return (
      <div className="min-h-screen bg-ui-lighter pt-20 px-6">
        <div className="max-w-[1800px] mx-auto bg-white rounded-lg shadow-lg p-6 text-ui">
          Loading…
        </div>
      </div>
    );
  }

  const isActive = moment().isBefore(moment(league.expiry_date));
  const tabs = [
    { key: 'students', label: T.Teams },
    { key: 'tutorials', label: `${T.Tutorial} Progress` },
    { key: 'submissions', label: 'Submissions' },
    { key: 'simulation', label: 'Simulation' },
    { key: 'settings', label: 'Settings' },
  ];

  const copyLoginLink = () => {
    navigator.clipboard.writeText(
      `${window.location.origin}/join/${league.signup_link}`
    );
    toast.success('Login link copied to clipboard!');
  };

  return (
    <div className="min-h-screen bg-ui-lighter pt-20 px-6 pb-8">
      <div className="max-w-[1800px] mx-auto">
        {/* Header */}
        <div className="mb-4">
          <Link
            to="/InstitutionHome"
            className="text-sm text-primary hover:underline"
          >
            ← {`All ${T.leagues}`}
          </Link>
          <div className="flex flex-wrap items-center gap-3 mt-1">
            <h1 className="text-2xl font-bold text-ui-dark">{league.name}</h1>
            <span className="text-ui">{league.game}</span>
            <span
              className={`px-3 py-0.5 rounded-full text-sm font-medium ${
                isActive
                  ? 'bg-success-light text-success'
                  : 'bg-danger-light text-danger'
              }`}
            >
              {isActive ? 'Active' : 'Expired'}
            </span>
            {league.signup_link && (
              <button
                onClick={copyLoginLink}
                className="px-3 py-1 text-sm bg-primary hover:bg-primary-hover text-white rounded-lg transition-colors"
                title={`Copy the ${T.team} login link for this ${T.league}`}
              >
                Copy login link
              </button>
            )}
          </div>
        </div>

        {/* Tab bar */}
        <div className="flex flex-wrap gap-1 border-b border-ui-light mb-6">
          {tabs.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => navigate(`/Classroom/${leagueId}/${key}`)}
              className={`px-4 py-2 text-base font-medium rounded-t-lg transition-colors ${
                activeTab === key
                  ? 'bg-white text-primary border border-b-0 border-ui-light'
                  : 'text-ui hover:text-ui-dark hover:bg-white/60'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        {activeTab === 'students' && <StudentsTab league={league} />}
        {activeTab === 'tutorials' && <TutorialMatrixTab league={league} />}
        {activeTab === 'submissions' && <SubmissionsTab league={league} />}
        {activeTab === 'simulation' && <SimulationPanel userRole="institution" />}
        {activeTab === 'settings' && (
          <LeagueDetailsPanel
            userRole="institution"
            showTeams={false}
            onDeleted={() => navigate('/InstitutionHome')}
          />
        )}
      </div>
    </div>
  );
}

export default ClassroomWorkspace;
