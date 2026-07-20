import React, { useState, useEffect, useCallback } from 'react';
import { toast } from 'react-toastify';
import { useNavigate, useLocation } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { authFetch } from '../../utils/authFetch';
import { selectToken } from '../../slices/authSlice';
import { setCurrentLeague } from '../../slices/leaguesSlice';
import useLeagueAPI from '../Shared/hooks/useLeagueAPI';
import { useTerms } from '../Shared/terminology';

// Display labels for the plan tiers (the price/amount is driven server-side).
const TIER_LABELS = {
  club: 'Club & School',
  university: 'University & Large Cohort',
  teacher: 'Teacher',
  school: 'Whole School',
};

const PAYMENT_METHOD_LABELS = {
  card: 'Card',
  invoice: 'Invoice',
  admin: 'Manually granted',
};

function formatDate(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

// "greedy_pig" -> "Greedy Pig"
function formatGameName(game) {
  if (!game) return '—';
  return game
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

function Row({ label, children }) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-baseline py-2 border-b border-ui-light last:border-b-0">
      <span className="w-full sm:w-1/3 text-sm font-medium text-ui">{label}</span>
      <span className="w-full sm:w-2/3 text-ui-dark">{children}</span>
    </div>
  );
}

function InstitutionHome() {
  const T = useTerms();
  const navigate = useNavigate();
  const location = useLocation();
  const dispatch = useDispatch();
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const accessToken = useSelector(selectToken);
  const { fetchUserLeagues } = useLeagueAPI('institution');

  const [isLoading, setIsLoading] = useState(true);
  const [data, setData] = useState(null);
  // league id whose signup link is currently being generated
  const [generatingFor, setGeneratingFor] = useState(null);

  // Passed through from the invoiced signup flow so the hosted invoice link
  // isn't lost after auto-login. Only present right after signup.
  const hostedInvoiceUrl = location.state?.hostedInvoiceUrl || null;

  const fetchHome = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await authFetch(`${apiUrl}/institution/home`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      const json = await response.json();
      if (response.ok) {
        setData(json);
      } else {
        toast.error(json.detail || 'Could not load your home page');
      }
    } catch (error) {
      console.error('Error fetching home data:', error);
      toast.error('Could not reach the server. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }, [apiUrl, accessToken]);

  useEffect(() => {
    fetchHome();
  }, [fetchHome]);

  const loginUrlFor = (classroom) =>
    `${window.location.origin}/join/${classroom.signup_link}`;

  const copyLoginLink = (classroom) => {
    navigator.clipboard.writeText(loginUrlFor(classroom));
    toast.success('Login link copied to clipboard!');
  };

  const createLoginLink = async (classroom) => {
    setGeneratingFor(classroom.id);
    try {
      const response = await authFetch(
        `${apiUrl}/institution/generate-signup-link`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${accessToken}`,
          },
          body: JSON.stringify({ league_id: classroom.id }),
        }
      );
      const json = await response.json();
      if (response.ok && json.signup_token) {
        setData((prev) => ({
          ...prev,
          classrooms: prev.classrooms.map((c) =>
            c.id === classroom.id ? { ...c, signup_link: json.signup_token } : c
          ),
        }));
        toast.success(`Login link created for ${classroom.name}`);
      } else {
        toast.error(json.detail || 'Failed to create the login link');
      }
    } catch (error) {
      console.error('Error generating signup link:', error);
      toast.error('Network error while creating the login link');
    } finally {
      setGeneratingFor(null);
    }
  };

  // Open League/Classroom Management with this classroom pre-selected: the
  // leagues list must be in Redux before setCurrentLeague can find it by name.
  const openManagement = async (classroom) => {
    await fetchUserLeagues();
    dispatch(setCurrentLeague(classroom.name));
    navigate('/InstitutionLeague');
  };

  const card = 'bg-white rounded-lg shadow-lg p-6';
  const classrooms = data?.classrooms || [];
  const activeClassrooms = classrooms.filter((c) => c.is_active);
  const expiredClassrooms = classrooms.filter((c) => !c.is_active);
  const sub = data?.subscription;
  const subActive = sub?.subscription_active;

  return (
    <div className="min-h-screen pt-16 bg-ui-lighter">
      <div className="w-full max-w-6xl mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold text-ui-dark mb-2">
          {data?.institution_name ? `Welcome, ${data.institution_name}` : 'Home'}
        </h1>
        <p className="text-ui mb-6">
          {`Your active ${T.leagues} at a glance — share a login link with your ${T.teams} to get them started.`}
        </p>

        {hostedInvoiceUrl && (
          <div className="mb-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-ui-dark">
              Your invoice has been issued and emailed (net 30 — no payment
              needed now).{' '}
              <a
                href={hostedInvoiceUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary underline font-medium"
              >
                View or download your invoice
              </a>
            </p>
          </div>
        )}

        {isLoading ? (
          <div className={`${card} text-center text-ui`}>Loading…</div>
        ) : !data ? (
          <div className={`${card} text-center text-ui`}>
            Nothing to show yet.
          </div>
        ) : (
          <div className="space-y-8">
            {/* Active classrooms/leagues */}
            <section>
              <h2 className="text-2xl font-semibold text-ui-dark mb-4">
                {`Active ${T.Leagues}`}
              </h2>

              {activeClassrooms.length === 0 ? (
                <div className={`${card} text-ui`}>
                  {`You have no active ${T.leagues} yet. `}
                  <button
                    onClick={() => navigate('/InstitutionLeague')}
                    className="text-primary font-semibold underline"
                  >
                    {`Create one in ${T.League} Management`}
                  </button>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {activeClassrooms.map((classroom) => (
                    <div key={classroom.id} className={card}>
                      <div className="flex justify-between items-start mb-4">
                        <button
                          onClick={() => openManagement(classroom)}
                          className="text-left"
                          title={`Open ${classroom.name} in ${T.League} Management`}
                        >
                          <span className="flex items-center gap-2">
                            <span className="w-2.5 h-2.5 rounded-full bg-success"></span>
                            <span className="text-xl font-semibold text-primary hover:underline">
                              {classroom.name}
                            </span>
                          </span>
                        </button>
                        <span className="text-sm font-medium text-ui-dark bg-ui-lighter px-3 py-1 rounded-full whitespace-nowrap">
                          {`${classroom.team_count} ${
                            classroom.team_count === 1 ? T.team : T.teams
                          }`}
                        </span>
                      </div>

                      <div className="space-y-3 mb-4">
                        <div>
                          <span className="text-sm font-medium text-ui">Game: </span>
                          <span className="text-ui-dark font-medium">
                            {formatGameName(classroom.game)}
                          </span>
                        </div>
                        <div>
                          <span className="block text-sm font-medium text-ui mb-1">
                            Tutorials:
                          </span>
                          {classroom.tutorials.length > 0 ? (
                            <div className="flex flex-wrap gap-1.5">
                              {classroom.tutorials.map((title) => (
                                <span
                                  key={title}
                                  className="text-xs bg-primary-light/20 text-primary-dark px-2 py-0.5 rounded-full"
                                >
                                  {title}
                                </span>
                              ))}
                            </div>
                          ) : (
                            <span className="text-sm text-ui">
                              No tutorials selected
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="pt-3 border-t border-ui-light">
                        <span className="block text-sm font-medium text-ui mb-2">
                          {`${T.Team} login link:`}
                        </span>
                        {classroom.signup_link ? (
                          <div className="flex items-center gap-2">
                            <input
                              type="text"
                              value={loginUrlFor(classroom)}
                              readOnly
                              onFocus={(e) => e.target.select()}
                              className="flex-1 p-2 border border-ui-light rounded-lg text-sm bg-ui-lighter"
                            />
                            <button
                              onClick={() => copyLoginLink(classroom)}
                              className="px-3 py-2 bg-primary hover:bg-primary-hover text-white rounded-lg text-sm font-medium"
                              title="Copy to clipboard"
                            >
                              Copy
                            </button>
                          </div>
                        ) : (
                          <button
                            onClick={() => createLoginLink(classroom)}
                            disabled={generatingFor === classroom.id}
                            className="px-4 py-2 bg-primary hover:bg-primary-hover text-white rounded-lg text-sm font-medium transition-colors disabled:bg-ui-light disabled:cursor-not-allowed"
                          >
                            {generatingFor === classroom.id
                              ? 'Creating…'
                              : 'Create login link'}
                          </button>
                        )}
                        <p className="mt-2 text-xs text-ui">
                          {`Share this link with your ${T.teams} — they use it to sign up and log in to this ${T.league}.`}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {expiredClassrooms.length > 0 && (
                <div className="mt-4 text-sm text-ui">
                  {`Expired ${T.leagues}: `}
                  {expiredClassrooms.map((classroom, i) => (
                    <span key={classroom.id}>
                      {i > 0 && ', '}
                      <button
                        onClick={() => openManagement(classroom)}
                        className="underline hover:text-primary"
                      >
                        {classroom.name}
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </section>

            {/* Subscription */}
            <section>
              <h2 className="text-2xl font-semibold text-ui-dark mb-4">
                Subscription
              </h2>
              <div className={card}>
                {sub ? (
                  <div>
                    <Row label="Plan">
                      {TIER_LABELS[sub.tier] || sub.tier || 'Subscription'}
                    </Row>
                    <Row label="Status">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-sm font-medium ${
                          subActive
                            ? 'bg-green-100 text-green-800'
                            : 'bg-red-100 text-red-800'
                        }`}
                      >
                        {subActive ? 'Active' : 'Inactive'}
                      </span>
                    </Row>
                    <Row label="Expires">{formatDate(sub.subscription_expiry)}</Row>
                    <Row label="Auto-renew">{sub.auto_renew ? 'Yes' : 'No'}</Row>
                    <Row label="Billed via">
                      {PAYMENT_METHOD_LABELS[sub.payment_method] ||
                        sub.payment_method ||
                        '—'}
                    </Row>
                    <Row label="Contact">
                      {[data.contact_person, data.contact_email]
                        .filter(Boolean)
                        .join(' — ') || '—'}
                    </Row>
                  </div>
                ) : (
                  <p className="text-ui">No active subscription on record.</p>
                )}
              </div>
            </section>
          </div>
        )}
      </div>
    </div>
  );
}

export default InstitutionHome;
