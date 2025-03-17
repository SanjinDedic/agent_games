import React, { useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import { useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import moment from 'moment-timezone';
import { checkTokenExpiry } from '../../slices/authSlice';
import DemoUserCard from './DemoUserCard';

function AdminDemoUsers() {
    const navigate = useNavigate();
    const dispatch = useDispatch();
    const apiUrl = useSelector((state) => state.settings.agentApiUrl);
    const accessToken = useSelector((state) => state.auth.token);
    const currentUser = useSelector((state) => state.auth.currentUser);
    const isAuthenticated = useSelector((state) => state.auth.isAuthenticated);

    const [demoUsers, setDemoUsers] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isDeletingAll, setIsDeletingAll] = useState(false);

    // Check authentication and fetch demo users on component mount
    useEffect(() => {
        const tokenExpired = dispatch(checkTokenExpiry());
        if (!isAuthenticated || currentUser.role !== "admin" || tokenExpired) {
            navigate('/Admin');
            return;
        }

        fetchDemoUsers();
    }, [navigate, dispatch, isAuthenticated, currentUser]);

    // Fetch all demo users
    const fetchDemoUsers = async () => {
        setIsLoading(true);
        try {
            const response = await fetch(`${apiUrl}/admin/get_all_demo_users`, {
                headers: {
                    'Authorization': `Bearer ${accessToken}`
                }
            });

            const data = await response.json();

            if (data.status === "success") {
                // Make sure demo_users exists and handle any None/null values
                const demoUsers = data.data?.demo_users || [];
                // Ensure all user objects have an email property, even if it's null
                setDemoUsers(demoUsers.map(user => ({
                    ...user,
                    email: user.email !== undefined ? user.email : null
                })));
            } else {
                toast.error(data.message || 'Failed to fetch demo users');
            }
        } catch (error) {
            console.error('Error fetching demo users:', error);
            toast.error('Network error while fetching demo users');
        } finally {
            setIsLoading(false);
        }
    };

    // Delete all demo users
    const handleDeleteAll = async () => {
        if (!window.confirm('Are you sure you want to delete ALL demo users? This action cannot be undone.')) {
            return;
        }

        setIsDeletingAll(true);
        try {
            const response = await fetch(`${apiUrl}/admin/delete_demo_teams_and_subs`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${accessToken}`
                }
            });

            const data = await response.json();

            if (data.status === "success") {
                toast.success('All demo users deleted successfully');
                setDemoUsers([]);
            } else {
                toast.error(data.message || 'Failed to delete demo users');
            }
        } catch (error) {
            console.error('Error deleting demo users:', error);
            toast.error('Network error while deleting demo users');
        } finally {
            setIsDeletingAll(false);
        }
    };

    // Refresh the demo users list
    const handleRefresh = () => {
        fetchDemoUsers();
    };

    // Delete a single demo user using the delete-team endpoint
    const handleDeleteUser = async (teamId, teamName) => {
        if (!window.confirm(`Are you sure you want to delete demo user ${teamName}?`)) {
            return;
        }

        try {
            const response = await fetch(`${apiUrl}/admin/delete-team`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${accessToken}`
                },
                body: JSON.stringify({ id: teamId })
            });

            const data = await response.json();

            if (data.status === "success") {
                toast.success(`Demo user ${teamName} deleted successfully`);
                setDemoUsers(demoUsers.filter(user => user.demo_team_id !== teamId));
            } else {
                toast.error(data.message || 'Failed to delete demo user');
            }
        } catch (error) {
            console.error('Error deleting demo user:', error);
            toast.error('Network error while deleting demo user');
        }
    };

    return (
        <div className="min-h-screen bg-ui-lighter pt-20 px-6 pb-8">
            <div className="max-w-[1800px] mx-auto">
                <div className="bg-white rounded-lg shadow-lg p-6">
                    <div className="flex justify-between items-center mb-6">
                        <h1 className="text-2xl font-bold text-ui-dark">Demo Users Management</h1>
                        <div className="flex space-x-4">
                            <button
                                onClick={handleRefresh}
                                className="px-4 py-2 bg-primary hover:bg-primary-hover text-white rounded-lg transition-colors"
                                disabled={isLoading}
                            >
                                {isLoading ? 'Refreshing...' : 'Refresh'}
                            </button>
                            <button
                                onClick={handleDeleteAll}
                                className="px-4 py-2 bg-danger hover:bg-danger-hover text-white rounded-lg transition-colors"
                                disabled={isDeletingAll || demoUsers.length === 0}
                            >
                                {isDeletingAll ? 'Deleting...' : 'Delete All Demo Users'}
                            </button>
                        </div>
                    </div>

                    {isLoading ? (
                        <div className="flex justify-center items-center h-32">
                            <div className="text-lg text-ui-dark">Loading demo users...</div>
                        </div>
                    ) : demoUsers.length === 0 ? (
                        <div className="text-center py-8">
                            <p className="text-lg text-ui">No demo users found.</p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            {demoUsers.map((user) => (
                                <DemoUserCard
                                    key={user.demo_team_id}
                                    user={user}
                                    onDelete={() => handleDeleteUser(user.demo_team_id, user.demo_team_name)}
                                />
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

export default AdminDemoUsers;