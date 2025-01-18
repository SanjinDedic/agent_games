import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { toast } from 'react-toastify';
import { checkTokenExpiry } from '../../slices/authSlice';

function DockerStatus() {
    const navigate = useNavigate();
    const dispatch = useDispatch();
    const apiUrl = useSelector((state) => state.settings.agentApiUrl);
    const accessToken = useSelector((state) => state.auth.token);
    const currentUser = useSelector((state) => state.auth.currentUser);
    const isAuthenticated = useSelector((state) => state.auth.isAuthenticated);

    const [validatorLogs, setValidatorLogs] = useState('');
    const [simulatorLogs, setSimulatorLogs] = useState('');
    const [isValidatorLoading, setIsValidatorLoading] = useState(false);
    const [isSimulatorLoading, setIsSimulatorLoading] = useState(false);
    const [validatorHealth, setValidatorHealth] = useState(false);
    const [simulatorHealth, setSimulatorHealth] = useState(false);
    const [showValidatorLogs, setShowValidatorLogs] = useState(true);
    const [showSimulatorLogs, setShowSimulatorLogs] = useState(true);

    useEffect(() => {
        const tokenExpired = dispatch(checkTokenExpiry());
        if (!isAuthenticated || currentUser.role !== "admin" || tokenExpired) {
            navigate('/Admin');
        }

        // Initial checks
        checkHealth();
        fetchLogs();

        // Set up interval for health checks
        const healthCheckInterval = setInterval(checkHealth, 30000);

        return () => clearInterval(healthCheckInterval);
    }, [navigate]);

    const checkHealth = async () => {
        try {
            // Check validator health
            const validatorResponse = await fetch(`${apiUrl}/admin/get-validator-logs?health=true`, {
                headers: { 'Authorization': `Bearer ${accessToken}` }
            });
            const validatorData = await validatorResponse.json();
            setValidatorHealth(validatorData.status === "success");

            // Check simulator health
            const simulatorResponse = await fetch(`${apiUrl}/admin/get-simulator-logs?health=true`, {
                headers: { 'Authorization': `Bearer ${accessToken}` }
            });
            const simulatorData = await simulatorResponse.json();
            setSimulatorHealth(simulatorData.status === "success");
        } catch (error) {
            console.error('Error checking health:', error);
            setValidatorHealth(false);
            setSimulatorHealth(false);
        }
    };

    const fetchLogs = async () => {
        await Promise.all([
            fetchValidatorLogs(),
            fetchSimulatorLogs()
        ]);
    };

    const fetchValidatorLogs = async () => {
        setIsValidatorLoading(true);
        try {
            const response = await fetch(`${apiUrl}/admin/get-validator-logs`, {
                headers: { 'Authorization': `Bearer ${accessToken}` }
            });
            const data = await response.json();
            if (data.status === "success") {
                setValidatorLogs(data.data.logs);
            } else {
                toast.error('Failed to fetch validator logs');
            }
        } catch (error) {
            console.error('Error fetching validator logs:', error);
        } finally {
            setIsValidatorLoading(false);
        }
    };

    const fetchSimulatorLogs = async () => {
        setIsSimulatorLoading(true);
        try {
            const response = await fetch(`${apiUrl}/admin/get-simulator-logs`, {
                headers: { 'Authorization': `Bearer ${accessToken}` }
            });
            const data = await response.json();
            if (data.status === "success") {
                setSimulatorLogs(data.data.logs);
            } else {
                toast.error('Failed to fetch simulator logs');
            }
        } catch (error) {
            console.error('Error fetching simulator logs:', error);
        } finally {
            setIsSimulatorLoading(false);
        }
    };

    const ServiceStatus = ({ name, isHealthy, isLoading, showLogs, onToggleLogs, onRefresh }) => (
        <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
            <div className="flex justify-between items-center mb-4">
                <div className="flex items-center gap-4">
                    <h2 className="text-xl font-bold text-ui-dark">{name} Status</h2>
                    <div className="flex items-center gap-2">
                        <div className={`w-3 h-3 rounded-full ${isHealthy ? 'bg-success' : 'bg-danger'}`} />
                        <span className={`text-sm font-medium ${isHealthy ? 'text-success' : 'text-danger'}`}>
                            {isHealthy ? 'Healthy' : 'Unhealthy'}
                        </span>
                    </div>
                </div>
                <div className="flex items-center gap-4">
                    <button
                        onClick={onToggleLogs}
                        className="text-ui hover:text-ui-dark transition-colors"
                    >
                        {showLogs ? '▼' : '▶'}
                    </button>
                    <button
                        onClick={onRefresh}
                        disabled={isLoading}
                        className="bg-primary hover:bg-primary-hover text-white px-4 py-2 rounded-lg transition-colors duration-200 disabled:opacity-50"
                    >
                        {isLoading ? 'Refreshing...' : 'Refresh Logs'}
                    </button>
                </div>
            </div>

            {showLogs && (
                <div className="bg-ui-dark rounded-lg p-4 overflow-x-auto">
                    <pre className="text-white font-mono text-sm whitespace-pre-wrap">
                        {name === 'Validator' ? validatorLogs : simulatorLogs || 'No logs available'}
                    </pre>
                </div>
            )}
        </div>
    );

    return (
        <div className="min-h-screen bg-ui-lighter pt-20 px-6 pb-8">
            <div className="max-w-[1800px] mx-auto">
                <ServiceStatus
                    name="Validator"
                    isHealthy={validatorHealth}
                    isLoading={isValidatorLoading}
                    showLogs={showValidatorLogs}
                    onToggleLogs={() => setShowValidatorLogs(!showValidatorLogs)}
                    onRefresh={fetchValidatorLogs}
                />
                <ServiceStatus
                    name="Simulator"
                    isHealthy={simulatorHealth}
                    isLoading={isSimulatorLoading}
                    showLogs={showSimulatorLogs}
                    onToggleLogs={() => setShowSimulatorLogs(!showSimulatorLogs)}
                    onRefresh={fetchSimulatorLogs}
                />
            </div>
        </div>
    );
}

export default DockerStatus;