import React, { useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import { useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { checkTokenExpiry } from '../../slices/authSlice';
import { authFetch } from '../../utils/authFetch';

function AdminBackup() {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const accessToken = useSelector((state) => state.auth.token);
  const currentUser = useSelector((state) => state.auth.currentUser);
  const isAuthenticated = useSelector((state) => state.auth.isAuthenticated);

  const [backups, setBackups] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [restoringKey, setRestoringKey] = useState(null);

  useEffect(() => {
    const tokenExpired = dispatch(checkTokenExpiry());
    if (!isAuthenticated || currentUser.role !== 'admin' || tokenExpired) {
      navigate('/Admin');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    fetchBackups();
  }, [apiUrl, accessToken]);

  const fetchBackups = () => {
    setIsLoading(true);
    authFetch(`${apiUrl}/admin/list-backups`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.status === 'success') {
          setBackups(data.data.backups || []);
        } else {
          toast.error(data.message || 'Failed to load backups');
        }
        setIsLoading(false);
      })
      .catch((err) => {
        console.error('Error fetching backups:', err);
        toast.error('Error connecting to server');
        setIsLoading(false);
      });
  };

  const handleCreateBackup = () => {
    if (!window.confirm('Create a new database backup? This may take a moment.')) return;

    setIsCreating(true);
    authFetch(`${apiUrl}/admin/backup-database`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${accessToken}`,
      },
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.status === 'success') {
          toast.success(data.message || 'Backup created successfully');
          fetchBackups();
        } else {
          toast.error(data.message || 'Backup failed');
        }
        setIsCreating(false);
      })
      .catch((err) => {
        console.error('Error creating backup:', err);
        toast.error('Error connecting to server');
        setIsCreating(false);
      });
  };

  const handleRestore = (backup) => {
    if (!window.confirm(
      `WARNING: This will DROP the current database and restore from "${backup.filename}". This cannot be undone. Are you sure?`
    )) return;

    if (!window.confirm(
      'This is your last chance to cancel. All current data will be permanently replaced. Continue?'
    )) return;

    setRestoringKey(backup.s3_key);
    authFetch(`${apiUrl}/admin/restore-database`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({ s3_key: backup.s3_key }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.status === 'success') {
          toast.success(data.message || 'Database restored successfully');
        } else {
          toast.error(data.message || 'Restore failed');
        }
        setRestoringKey(null);
      })
      .catch((err) => {
        console.error('Error restoring backup:', err);
        toast.error('Error connecting to server');
        setRestoringKey(null);
      });
  };

  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (iso) => {
    return new Date(iso).toLocaleString();
  };

  return (
    <div className="min-h-screen bg-ui-lighter pt-20 px-6 pb-8">
      <div className="max-w-7xl mx-auto">
        <div className="bg-white rounded-lg shadow-lg p-6">
          <div className="flex justify-between items-center mb-6">
            <h1 className="text-2xl font-bold text-ui-dark">Database Backups</h1>
            <button
              onClick={handleCreateBackup}
              disabled={isCreating}
              className="px-4 py-2 bg-success hover:bg-success-hover text-white rounded-lg transition-colors disabled:opacity-50"
            >
              {isCreating ? 'Creating Backup...' : 'Create Backup'}
            </button>
          </div>

          {isLoading ? (
            <div className="flex justify-center items-center h-32">
              <div className="text-lg text-ui-dark">Loading backups...</div>
            </div>
          ) : backups.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-lg text-ui">No backups found. Create one to get started.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse">
                <thead>
                  <tr className="bg-ui-lighter">
                    <th className="px-4 py-2 text-left text-ui-dark">Filename</th>
                    <th className="px-4 py-2 text-left text-ui-dark">Size</th>
                    <th className="px-4 py-2 text-left text-ui-dark">Date</th>
                    <th className="px-4 py-2 text-left text-ui-dark">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {backups.map((backup) => (
                    <tr key={backup.s3_key} className="border-b border-ui-light hover:bg-ui-lighter/50">
                      <td className="px-4 py-3 font-mono text-sm">{backup.filename}</td>
                      <td className="px-4 py-3">{formatSize(backup.size_bytes)}</td>
                      <td className="px-4 py-3">{formatDate(backup.last_modified)}</td>
                      <td className="px-4 py-3">
                        <button
                          onClick={() => handleRestore(backup)}
                          disabled={restoringKey !== null}
                          className="px-3 py-1 bg-primary hover:bg-primary-hover text-white text-sm rounded transition-colors disabled:opacity-50"
                        >
                          {restoringKey === backup.s3_key ? 'Restoring...' : 'Restore'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default AdminBackup;
