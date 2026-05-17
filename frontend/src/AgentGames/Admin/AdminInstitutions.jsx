import React, { useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import { useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { checkTokenExpiry } from '../../slices/authSlice';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import moment from 'moment-timezone';
import { saveAs } from 'file-saver';
import { authFetch } from '../../utils/authFetch';

function AdminInstitutions() {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const accessToken = useSelector((state) => state.auth.token);
  const currentUser = useSelector((state) => state.auth.currentUser);
  const isAuthenticated = useSelector((state) => state.auth.isAuthenticated);
  
  const [institutions, setInstitutions] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [institutionForm, setInstitutionForm] = useState({
    name: '',
    contact_person: '',
    contact_email: '',
    password: '',
    subscription_expiry: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000), // Default to 1 year
    docker_access: false
  });

  useEffect(() => {
    const tokenExpired = dispatch(checkTokenExpiry());
    if (!isAuthenticated || currentUser.role !== "admin" || tokenExpired) {
      navigate('/Admin');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    fetchInstitutions();
  }, [apiUrl, accessToken]);

  const fetchInstitutions = () => {
    setIsLoading(true);
    authFetch(`${apiUrl}/admin/get-all-institutions`, {
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    })
      .then(response => response.json())
      .then(data => {
        if (data.status === "success") {
          setInstitutions(data.data.institutions || []);
        } else {
          toast.error(data.message || 'Failed to load institutions');
        }
        setIsLoading(false);
      })
      .catch(error => {
        console.error('Error fetching institutions:', error);
        toast.error('Error connecting to server');
        setIsLoading(false);
      });
  };

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setInstitutionForm(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleDateChange = (date) => {
    setInstitutionForm(prev => ({
      ...prev,
      subscription_expiry: date
    }));
  };

  const handleCreateInstitution = (e) => {
    e.preventDefault();
    
    // Basic validation
    if (!institutionForm.name.trim() || !institutionForm.contact_person.trim() || 
        !institutionForm.contact_email.trim() || !institutionForm.password.trim()) {
      toast.error('Please fill in all required fields');
      return;
    }

    setIsLoading(true);
    authFetch(`${apiUrl}/admin/institution-create`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      },
      body: JSON.stringify(institutionForm),
    })
      .then(response => response.json())
      .then(data => {
        if (data.status === "success") {
          toast.success('Institution created successfully');
          setShowAddForm(false);
          setInstitutionForm({
            name: '',
            contact_person: '',
            contact_email: '',
            password: '',
            subscription_expiry: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000),
            docker_access: false
          });
          fetchInstitutions(); // Refresh the list
        } else {
          toast.error(data.message || 'Failed to create institution');
        }
        setIsLoading(false);
      })
      .catch(error => {
        console.error('Error creating institution:', error);
        toast.error('Error connecting to server');
        setIsLoading(false);
      });
  };

  const handleDeleteInstitution = (id, name) => {
    if (window.confirm(`Are you sure you want to delete institution "${name}"? This will delete all associated teams and leagues.`)) {
      setIsLoading(true);
      authFetch(`${apiUrl}/admin/institution-delete`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
        body: JSON.stringify({ id }),
      })
        .then(response => response.json())
        .then(data => {
          if (data.status === "success") {
            toast.success(data.message || 'Institution deleted successfully');
            fetchInstitutions(); // Refresh the list
          } else {
            toast.error(data.message || 'Failed to delete institution');
          }
          setIsLoading(false);
        })
        .catch(error => {
          console.error('Error deleting institution:', error);
          toast.error('Error connecting to server');
          setIsLoading(false);
        });
    }
  };

  const handleExportInstitution = (id, name) => {
    setIsLoading(true);
    authFetch(`${apiUrl}/admin/institution-export/${id}`, {
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    })
      .then(response => response.json())
      .then(data => {
        if (data.status === "success") {
          const blob = new Blob(
            [JSON.stringify(data.data, null, 2)],
            { type: 'application/json' }
          );
          const safeName = name.replace(/[^a-zA-Z0-9-_]+/g, '_');
          const dateStr = moment().format('YYYY-MM-DD');
          saveAs(blob, `${safeName}-export-${dateStr}.json`);
          toast.success('Institution data exported');
        } else {
          toast.error(data.message || 'Failed to export institution');
        }
        setIsLoading(false);
      })
      .catch(error => {
        console.error('Error exporting institution:', error);
        toast.error('Error connecting to server');
        setIsLoading(false);
      });
  };

  const handleClearInstitution = (id, name) => {
    const typed = window.prompt(
      `This will permanently delete every team, league (except "unassigned"), submission, simulation result, agent API key, and support ticket for "${name}".\n\nType the institution name exactly to confirm:`
    );
    if (typed === null) return;
    if (typed !== name) {
      toast.error('Confirmation text did not match — nothing was cleared');
      return;
    }

    setIsLoading(true);
    authFetch(`${apiUrl}/admin/institution-clear-data`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      },
      body: JSON.stringify({ id }),
    })
      .then(response => response.json())
      .then(data => {
        if (data.status === "success") {
          toast.success(data.message || 'Institution data cleared');
          fetchInstitutions();
        } else {
          toast.error(data.message || 'Failed to clear institution data');
        }
        setIsLoading(false);
      })
      .catch(error => {
        console.error('Error clearing institution data:', error);
        toast.error('Error connecting to server');
        setIsLoading(false);
      });
  };

  const toggleDockerAccess = (institutionId, enable) => {
    setIsLoading(true);
    authFetch(`${apiUrl}/admin/toggle-docker-access`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      },
      body: JSON.stringify({ institution_id: institutionId, enable }),
    })
      .then(response => response.json())
      .then(data => {
        if (data.status === "success") {
          toast.success(data.message || `Docker access ${enable ? 'enabled' : 'disabled'} successfully`);
          fetchInstitutions(); // Refresh the list
        } else {
          toast.error(data.message || 'Failed to update Docker access');
        }
        setIsLoading(false);
      })
      .catch(error => {
        console.error('Error updating Docker access:', error);
        toast.error('Error connecting to server');
        setIsLoading(false);
      });
  };

  return (
    <div className="min-h-screen bg-ui-lighter pt-20 px-6 pb-8">
      <div className="max-w-7xl mx-auto">
        <div className="bg-white rounded-lg shadow-lg p-6">
          <div className="flex justify-between items-center mb-6">
            <h1 className="text-2xl font-bold text-ui-dark">Institution Management</h1>
            <button
              onClick={() => setShowAddForm(!showAddForm)}
              className="px-4 py-2 bg-success hover:bg-success-hover text-white rounded-lg transition-colors"
            >
              {showAddForm ? 'Cancel' : 'Add Institution'}
            </button>
          </div>

          {showAddForm && (
            <div className="bg-ui-lighter p-6 rounded-lg mb-8">
              <h2 className="text-xl font-semibold text-ui-dark mb-4">Create New Institution</h2>
              <form onSubmit={handleCreateInstitution} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="name" className="block text-ui-dark mb-1">Institution Name *</label>
                    <input
                      type="text"
                      id="name"
                      name="name"
                      value={institutionForm.name}
                      onChange={handleInputChange}
                      className="w-full p-2 border border-ui-light rounded-lg"
                      required
                    />
                  </div>
                  <div>
                    <label htmlFor="contact_person" className="block text-ui-dark mb-1">Contact Person *</label>
                    <input
                      type="text"
                      id="contact_person"
                      name="contact_person"
                      value={institutionForm.contact_person}
                      onChange={handleInputChange}
                      className="w-full p-2 border border-ui-light rounded-lg"
                      required
                    />
                  </div>
                  <div>
                    <label htmlFor="contact_email" className="block text-ui-dark mb-1">Contact Email *</label>
                    <input
                      type="email"
                      id="contact_email"
                      name="contact_email"
                      value={institutionForm.contact_email}
                      onChange={handleInputChange}
                      className="w-full p-2 border border-ui-light rounded-lg"
                      required
                    />
                  </div>
                  <div>
                    <label htmlFor="password" className="block text-ui-dark mb-1">Password *</label>
                    <input
                      type="password"
                      id="password"
                      name="password"
                      value={institutionForm.password}
                      onChange={handleInputChange}
                      className="w-full p-2 border border-ui-light rounded-lg"
                      required
                    />
                  </div>
                  <div>
                    <label htmlFor="subscription_expiry" className="block text-ui-dark mb-1">Subscription Expiry *</label>
                    <DatePicker
                      selected={institutionForm.subscription_expiry}
                      onChange={handleDateChange}
                      className="w-full p-2 border border-ui-light rounded-lg"
                      dateFormat="dd/MM/yyyy"
                      minDate={new Date()}
                    />
                  </div>
                  <div className="flex items-center">
                    <input
                      type="checkbox"
                      id="docker_access"
                      name="docker_access"
                      checked={institutionForm.docker_access}
                      onChange={handleInputChange}
                      className="mr-2"
                    />
                    <label htmlFor="docker_access" className="text-ui-dark">Enable Docker Access</label>
                  </div>
                </div>
                <div className="flex justify-end">
                  <button
                    type="submit"
                    className="px-6 py-2 bg-primary hover:bg-primary-hover text-white rounded-lg transition-colors"
                    disabled={isLoading}
                  >
                    {isLoading ? 'Creating...' : 'Create Institution'}
                  </button>
                </div>
              </form>
            </div>
          )}

          {isLoading && !showAddForm ? (
            <div className="flex justify-center items-center h-32">
              <div className="text-lg text-ui-dark">Loading institutions...</div>
            </div>
          ) : (
            <>
              {institutions.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-lg text-ui">No institutions found. Create one to get started.</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse">
                    <thead>
                      <tr className="bg-ui-lighter">
                        <th className="px-4 py-2 text-left text-ui-dark">Name</th>
                        <th className="px-4 py-2 text-left text-ui-dark">Contact</th>
                        <th className="px-4 py-2 text-left text-ui-dark">Email</th>
                        <th className="px-4 py-2 text-left text-ui-dark">Teams</th>
                        <th className="px-4 py-2 text-left text-ui-dark">Leagues</th>
                        <th className="px-4 py-2 text-left text-ui-dark">Subscription</th>
                        <th className="px-4 py-2 text-left text-ui-dark">Docker Access</th>
                        <th className="px-4 py-2 text-left text-ui-dark">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {institutions.map((institution) => {
                        const isActive = institution.subscription_active && 
                                         moment(institution.subscription_expiry).isAfter(moment());
                        return (
                          <tr key={institution.id} className="border-b border-ui-light hover:bg-ui-lighter/50">
                            <td className="px-4 py-3">{institution.name}</td>
                            <td className="px-4 py-3">{institution.contact_person}</td>
                            <td className="px-4 py-3">{institution.contact_email}</td>
                            <td className="px-4 py-3">{institution.team_count}</td>
                            <td className="px-4 py-3">{institution.league_count}</td>
                            <td className="px-4 py-3">
                              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                                isActive ? 'bg-success-light text-success' : 'bg-danger-light text-danger'
                              }`}>
                                {isActive ? 'Active' : 'Expired'}
                              </span>
                              <div className="text-xs text-ui mt-1">
                                {moment(institution.subscription_expiry).format('MMM DD, YYYY')}
                              </div>
                            </td>
                            <td className="px-4 py-3">
                              <div className="flex items-center">
                                <button
                                  onClick={() => toggleDockerAccess(institution.id, !institution.docker_access)}
                                  className={`relative inline-flex items-center h-6 rounded-full w-11 transition-colors focus:outline-none ${
                                    institution.docker_access ? 'bg-success' : 'bg-ui-light'
                                  }`}
                                >
                                  <span
                                    className={`inline-block w-4 h-4 transform transition-transform bg-white rounded-full ${
                                      institution.docker_access ? 'translate-x-6' : 'translate-x-1'
                                    }`}
                                  />
                                </button>
                                <span className="ml-2 text-sm">
                                  {institution.docker_access ? 'Enabled' : 'Disabled'}
                                </span>
                              </div>
                            </td>
                            <td className="px-4 py-3">
                              <div className="flex items-center gap-3">
                                <button
                                  onClick={() => handleExportInstitution(institution.id, institution.name)}
                                  className="text-primary hover:text-primary-hover"
                                  title="Export Data (JSON)"
                                >
                                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                                    <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm6.293-12.707a1 1 0 011.414 0l4 4a1 1 0 01-1.414 1.414L11 7.414V13a1 1 0 11-2 0V7.414L6.707 9.707a1 1 0 01-1.414-1.414l4-4z" clipRule="evenodd" transform="rotate(180 10 10)" />
                                  </svg>
                                </button>
                                <button
                                  onClick={() => handleClearInstitution(institution.id, institution.name)}
                                  className="text-notice-orange hover:text-danger"
                                  title="Clear All Data (keeps institution)"
                                >
                                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                                    <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l6.518 11.59c.75 1.335-.213 2.98-1.742 2.98H3.482c-1.53 0-2.493-1.645-1.743-2.98L8.257 3.1zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                                  </svg>
                                </button>
                                <button
                                  onClick={() => handleDeleteInstitution(institution.id, institution.name)}
                                  className="text-danger hover:text-danger-hover"
                                  title="Delete Institution"
                                >
                                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                                    <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v3a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                                  </svg>
                                </button>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default AdminInstitutions;