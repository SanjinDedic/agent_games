import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { toast } from 'react-toastify';
import { checkTokenExpiry } from '../../slices/authSlice';
import { authFetch } from '../../utils/authFetch';

const providers = [
  {
    id: 'openai_api_key',
    name: 'OpenAI',
    provider_key: 'openai',
    description: 'Powers GPT models for AI hints, plagiarism detection, and other future AI features',
    placeholder: 'sk-...',
  },
];

function AdminAPIKeys() {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const accessToken = useSelector((state) => state.auth.token);
  const currentUser = useSelector((state) => state.auth.currentUser);
  const isAuthenticated = useSelector((state) => state.auth.isAuthenticated);

  const [keys, setKeys] = useState({
    openai_api_key: '',
  });
  const [editValues, setEditValues] = useState({
    openai_api_key: '',
  });
  const [showKeys, setShowKeys] = useState({
    openai_api_key: false,
  });
  const [validating, setValidating] = useState({
    openai_api_key: false,
  });
  // { status: 'valid'|'invalid'|'error', timestamp: string } or null
  const [validationResult, setValidationResult] = useState({
    openai_api_key: null,
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const tokenExpired = dispatch(checkTokenExpiry());
    if (!isAuthenticated || currentUser?.role !== 'admin' || tokenExpired) {
      navigate('/Admin');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    fetchKeys();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiUrl, accessToken]);

  const fetchKeys = async () => {
    setLoading(true);
    try {
      const response = await authFetch(`${apiUrl}/ai/api-keys`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      const data = await response.json();
      if (data.status === 'success') {
        setKeys(data.data);
      } else {
        toast.error(data.message || 'Failed to fetch API keys');
      }
    } catch (err) {
      toast.error('Network error: Failed to fetch API keys');
    } finally {
      setLoading(false);
    }
  };

  const saveKeys = async () => {
    const payload = {};
    let hasChanges = false;
    for (const provider of providers) {
      if (editValues[provider.id] !== '') {
        payload[provider.id] = editValues[provider.id];
        hasChanges = true;
      }
    }

    if (!hasChanges) {
      toast.info('No changes to save');
      return;
    }

    setSaving(true);
    try {
      const response = await authFetch(`${apiUrl}/ai/api-keys`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (data.status === 'success') {
        setKeys(data.data);
        setEditValues({
          openai_api_key: '',
        });
        // Clear validation results for keys that were updated
        setValidationResult((prev) => {
          const next = { ...prev };
          for (const key of Object.keys(payload)) {
            next[key] = null;
          }
          return next;
        });
        toast.success('API keys updated successfully');
      } else {
        toast.error(data.message || 'Failed to update API keys');
      }
    } catch (err) {
      toast.error('Network error: Failed to update API keys');
    } finally {
      setSaving(false);
    }
  };

  const formatTimestamp = () => {
    const now = new Date();
    return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const validateKey = async (provider) => {
    const hasEditValue = editValues[provider.id] !== '';
    const hasExistingKey = keys[provider.id] && keys[provider.id] !== '';

    if (!hasEditValue && !hasExistingKey) {
      toast.info('No key to validate — enter or save a key first');
      return;
    }

    setValidating((prev) => ({ ...prev, [provider.id]: true }));

    const body = { provider: provider.provider_key };
    // If there's an edit value, validate that; otherwise validate the stored key
    if (hasEditValue) {
      body.api_key = editValues[provider.id];
    }

    try {
      const response = await authFetch(`${apiUrl}/ai/api-keys/validate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify(body),
      });
      const data = await response.json();
      const timestamp = formatTimestamp();

      if (data.status === 'success' && data.data?.valid) {
        setValidationResult((prev) => ({
          ...prev,
          [provider.id]: { status: 'valid', timestamp },
        }));
        toast.success(`${provider.name} key is valid`);
      } else if (data.status === 'success') {
        setValidationResult((prev) => ({
          ...prev,
          [provider.id]: { status: 'invalid', timestamp },
        }));
        toast.error(`${provider.name} key is invalid`);
      } else {
        setValidationResult((prev) => ({
          ...prev,
          [provider.id]: { status: 'error', timestamp },
        }));
        toast.error(data.message || 'Validation failed');
      }
    } catch (err) {
      const timestamp = formatTimestamp();
      setValidationResult((prev) => ({
        ...prev,
        [provider.id]: { status: 'error', timestamp },
      }));
      toast.error('Network error: Failed to validate key');
    } finally {
      setValidating((prev) => ({ ...prev, [provider.id]: false }));
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 pt-20 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100 pt-20 px-6 pb-12">
      <div className="max-w-6xl mx-auto">
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <div className="flex justify-between items-center mb-6">
            <h1 className="text-2xl font-bold text-gray-800">API Keys Configuration</h1>
            <div className="flex space-x-4">
              <button
                onClick={() => navigate('/AdminInstitutions')}
                className="px-4 py-2 bg-gray-500 text-white rounded-md hover:bg-gray-600 transition-colors duration-200"
              >
                Back
              </button>
              <button
                onClick={saveKeys}
                disabled={saving}
                className={`px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 transition-colors duration-200 ${
                  saving ? 'opacity-70 cursor-not-allowed' : ''
                }`}
              >
                {saving ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </div>

          <p className="text-gray-600 mb-6">
            Manage API keys for AI providers. Keys are stored securely in the database and used by AI features
            (hints, plagiarism detection, etc.). Enter a new key and click Save, or click Validate to test a key
            against the provider.
          </p>

          <div className="space-y-6">
            {providers.map((provider) => {
              const maskedValue = keys[provider.id];
              const isConfigured = maskedValue && maskedValue !== '';
              const result = validationResult[provider.id];
              const isValidating = validating[provider.id];

              return (
                <div key={provider.id} className="border border-gray-200 rounded-lg p-5">
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-800">{provider.name}</h3>
                      <p className="text-sm text-gray-500">{provider.description}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      {result && (
                        <span
                          className={`px-2 py-1 rounded-full text-xs font-medium ${
                            result.status === 'valid'
                              ? 'bg-green-100 text-green-700'
                              : result.status === 'invalid'
                                ? 'bg-red-100 text-red-700'
                                : 'bg-yellow-100 text-yellow-700'
                          }`}
                        >
                          {result.status === 'valid'
                            ? `Validated ${result.timestamp}`
                            : result.status === 'invalid'
                              ? `Invalid ${result.timestamp}`
                              : `Error ${result.timestamp}`}
                        </span>
                      )}
                      <span
                        className={`px-3 py-1 rounded-full text-xs font-semibold ${
                          isConfigured
                            ? 'bg-green-100 text-green-800'
                            : 'bg-red-100 text-red-800'
                        }`}
                      >
                        {isConfigured ? 'Configured' : 'Not Set'}
                      </span>
                    </div>
                  </div>

                  {isConfigured && (
                    <div className="mb-3">
                      <label className="block text-sm font-medium text-gray-500 mb-1">
                        Current Key
                      </label>
                      <div className="bg-gray-50 px-3 py-2 rounded-md font-mono text-sm text-gray-700">
                        {maskedValue}
                      </div>
                    </div>
                  )}

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      {isConfigured ? 'Replace Key' : 'Set Key'}
                    </label>
                    <div className="flex gap-2">
                      <div className="relative flex-1">
                        <input
                          type={showKeys[provider.id] ? 'text' : 'password'}
                          value={editValues[provider.id]}
                          onChange={(e) =>
                            setEditValues({ ...editValues, [provider.id]: e.target.value })
                          }
                          placeholder={provider.placeholder}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent pr-14 font-mono text-sm"
                        />
                        <button
                          type="button"
                          onClick={() =>
                            setShowKeys({ ...showKeys, [provider.id]: !showKeys[provider.id] })
                          }
                          className="absolute right-2 top-1/2 -translate-y-1/2 text-xs px-2 py-1 text-gray-500 hover:text-gray-700"
                        >
                          {showKeys[provider.id] ? 'Hide' : 'Show'}
                        </button>
                      </div>
                      <button
                        onClick={() => validateKey(provider)}
                        disabled={isValidating}
                        className={`px-4 py-2 text-sm font-medium rounded-md transition-colors duration-200 whitespace-nowrap ${
                          isValidating
                            ? 'bg-yellow-100 text-yellow-700 cursor-wait'
                            : 'bg-blue-100 text-blue-700 hover:bg-blue-200'
                        }`}
                      >
                        {isValidating ? 'Checking...' : 'Validate'}
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

export default AdminAPIKeys;
