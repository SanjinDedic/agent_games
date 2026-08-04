import React, { useState, useEffect, useCallback } from 'react';
import { useSelector } from 'react-redux';
import { toast } from 'react-toastify';
import { selectToken } from '../../slices/authSlice';
import { authFetch } from '../../utils/authFetch';

const KINDS = [
  { kind: 'game', label: 'Game submissions' },
  { kind: 'exercise', label: 'Exercise submissions' },
];

const ENVIRONMENTS = [
  { env: 'pyodide', label: 'Pyodide (WASM)' },
  { env: 'lambda', label: 'Lambda (server)' },
];

function AdminCodeEnv() {
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const accessToken = useSelector(selectToken);

  const [stats, setStats] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const fetchStats = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await authFetch(`${apiUrl}/admin/code-env-stats`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }

      setStats(await response.json());
    } catch (error) {
      console.error('Error fetching code env stats:', error);
      toast.error(`Error: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  }, [apiUrl, accessToken]);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  const cellFor = (kind, env) => {
    const match = (stats?.stats || []).find(
      (row) => row.kind === kind && row.environment === env
    );
    return { users: match?.users || 0, calls: match?.calls || 0 };
  };

  const totalFor = (env) => {
    const match = stats?.totals?.[env];
    return { users: match?.users || 0, calls: match?.calls || 0 };
  };

  const renderCounts = ({ users, calls }) => (
    <div className="flex flex-col">
      <span className="text-2xl font-bold text-ui-dark">{calls}</span>
      <span className="text-sm text-ui">
        calls · {users} user{users === 1 ? '' : 's'}
      </span>
    </div>
  );

  return (
    <div className="min-h-screen bg-ui-lighter pt-20 px-6 pb-8">
      <div className="max-w-6xl mx-auto">
        <div className="flex flex-wrap justify-between items-center mb-6">
          <h1 className="text-2xl font-bold text-ui-dark">
            Code Environment Usage
          </h1>

          <button
            onClick={fetchStats}
            disabled={isLoading}
            className="bg-primary hover:bg-primary-hover text-white px-4 py-2 rounded-md transition-colors duration-200 disabled:opacity-50 mt-4 sm:mt-0"
          >
            {isLoading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>

        <p className="text-ui mb-6">
          Where submitted code ran: in the browser via Pyodide (WASM) or on
          the server path (Lambda). Counters survive demo-user cleanup, so
          they cover all traffic since tracking began.
        </p>

        {!stats ? (
          <div className="text-center p-4">Loading usage stats...</div>
        ) : (
          <div className="bg-white rounded-lg shadow-lg p-6 overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-ui-light">
                  <th className="py-3 pr-4 text-ui-dark"></th>
                  {ENVIRONMENTS.map(({ env, label }) => (
                    <th key={env} className="py-3 pr-4 text-lg text-ui-dark">
                      {label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {KINDS.map(({ kind, label }) => (
                  <tr key={kind} className="border-b border-ui-lighter">
                    <td className="py-4 pr-4 font-medium text-ui-dark">
                      {label}
                    </td>
                    {ENVIRONMENTS.map(({ env }) => (
                      <td key={env} className="py-4 pr-4">
                        {renderCounts(cellFor(kind, env))}
                      </td>
                    ))}
                  </tr>
                ))}
                <tr>
                  <td className="py-4 pr-4 font-bold text-ui-dark">
                    All submissions
                  </td>
                  {ENVIRONMENTS.map(({ env }) => (
                    <td key={env} className="py-4 pr-4">
                      {renderCounts(totalFor(env))}
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
            <p className="text-xs text-ui mt-4">
              "All submissions" counts each user once per environment even if
              they made both game and exercise submissions.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default AdminCodeEnv;
