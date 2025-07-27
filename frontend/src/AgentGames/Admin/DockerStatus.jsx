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

  // State for the simplified data
  const [serviceStatus, setServiceStatus] = useState(null);
  const [selectedService, setSelectedService] = useState("validator");
  const [logs, setLogs] = useState("");
  const [isLoading, setIsLoading] = useState({
    status: false,
    logs: false,
  });
  const [logLines, setLogLines] = useState(1000);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [activeTab, setActiveTab] = useState("status");

  // Only validator and simulator services available
  const services = ["validator", "simulator", "api"];

  useEffect(() => {
    const tokenExpired = dispatch(checkTokenExpiry());
    if (
      !isAuthenticated ||
      (currentUser.role !== "admin" &&
        (!currentUser.institution || !currentUser.institution.docker_access)) ||
      tokenExpired
    ) {
      navigate("/Admin");
    }

    // Initial data fetch
    fetchServiceStatus();
    fetchLogs(selectedService);

    // Set up auto-refresh
    let intervalId;
    if (autoRefresh) {
      intervalId = setInterval(() => {
        fetchServiceStatus();
        fetchLogs(selectedService);
      }, 10000); // Refresh every 10 seconds
    }

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [navigate, autoRefresh, selectedService]);

  const fetchServiceStatus = async () => {
    setIsLoading((prev) => ({ ...prev, status: true }));
    try {
      const response = await fetch(`${apiUrl}/diagnostics/status`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }

      const data = await response.json();
      if (data.status === "success") {
        setServiceStatus(data.data.statuses);
      } else {
        toast.error("Failed to fetch service status");
      }
    } catch (error) {
      console.error("Error fetching service status:", error);
      toast.error(`Error: ${error.message}`);
    } finally {
      setIsLoading((prev) => ({ ...prev, status: false }));
    }
  };

  const fetchLogs = async (service) => {
    setIsLoading((prev) => ({ ...prev, logs: true }));
    try {
      const response = await fetch(
        `${apiUrl}/diagnostics/logs?service=${service}&tail=${logLines}`,
        {
          headers: { Authorization: `Bearer ${accessToken}` },
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }

      const data = await response.json();
      if (data.status === "success") {
        setLogs(data.data.logs[service] || "No logs available");
      } else {
        toast.error("Failed to fetch logs");
      }
    } catch (error) {
      console.error("Error fetching logs:", error);
      toast.error(`Error: ${error.message}`);
    } finally {
      setIsLoading((prev) => ({ ...prev, logs: false }));
    }
  };

  const handleServiceChange = (e) => {
    const service = e.target.value;
    setSelectedService(service);
    fetchLogs(service);
  };

  const handleLogLinesChange = (e) => {
    setLogLines(parseInt(e.target.value));
  };

  const handleRefresh = () => {
    fetchServiceStatus();
    fetchLogs(selectedService);
  };

  // Render service status
  const renderServiceStatus = () => {
    if (!serviceStatus) {
      return <div className="text-center p-4">Loading service status...</div>;
    }

    return (
      <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
        <h2 className="text-xl font-bold text-ui-dark mb-4">Service Status</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Object.keys(serviceStatus).map((serviceName) => {
            const service = serviceStatus[serviceName];
            return (
              <div key={serviceName} className="bg-ui-lighter rounded-lg p-4">
                <div className="flex justify-between items-center mb-2">
                  <h3 className="font-medium text-lg capitalize">
                    {serviceName}
                  </h3>
                  <span
                    className={`px-3 py-1 text-sm font-semibold rounded-full ${
                      service.is_healthy
                        ? "bg-green-100 text-green-800"
                        : "bg-red-100 text-red-800"
                    }`}
                  >
                    {service.is_healthy ? "Healthy" : "Unhealthy"}
                  </span>
                </div>

                <div className="text-sm text-ui space-y-1">
                  <div>
                    <span className="font-medium">Status:</span>{" "}
                    <span
                      className={`px-2 py-1 text-xs rounded ${
                        service.status === "running"
                          ? "bg-green-100 text-green-800"
                          : "bg-red-100 text-red-800"
                      }`}
                    >
                      {service.status}
                    </span>
                  </div>
                  <div>
                    <span className="font-medium">Health:</span>{" "}
                    {service.health}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  // Render logs
  const renderLogs = () => {
    return (
      <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
        <div className="flex flex-wrap justify-between items-center mb-4">
          <h2 className="text-xl font-bold text-ui-dark">Service Logs</h2>

          <div className="flex flex-wrap gap-4 mt-2 sm:mt-0">
            <div className="flex items-center">
              <label
                htmlFor="service-select"
                className="mr-2 text-sm font-medium text-ui-dark"
              >
                Service:
              </label>
              <select
                id="service-select"
                value={selectedService}
                onChange={handleServiceChange}
                className="p-2 border border-gray-300 rounded-md text-sm"
              >
                {services.map((service) => (
                  <option key={service} value={service}>
                    {service}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center">
              <label
                htmlFor="log-lines"
                className="mr-2 text-sm font-medium text-ui-dark"
              >
                Lines:
              </label>
              <select
                id="log-lines"
                value={logLines}
                onChange={handleLogLinesChange}
                className="p-2 border border-gray-300 rounded-md text-sm"
              >
                <option value={100}>100</option>
                <option value={500}>500</option>
                <option value={1000}>1000</option>
              </select>
            </div>

            <button
              onClick={() => fetchLogs(selectedService)}
              disabled={isLoading.logs}
              className="bg-primary hover:bg-primary-hover text-white px-4 py-2 rounded-md transition-colors duration-200 disabled:opacity-50 text-sm"
            >
              {isLoading.logs ? "Loading..." : "Refresh Logs"}
            </button>
          </div>
        </div>

        <div className="bg-ui-dark rounded-lg p-4 overflow-x-auto h-96">
          <pre className="text-white font-mono text-sm whitespace-pre-wrap">
            {logs || "No logs available"}
          </pre>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-ui-lighter pt-20 px-6 pb-8">
      <div className="max-w-6xl mx-auto">
        {/* Header with controls */}
        <div className="flex flex-wrap justify-between items-center mb-6">
          <h1 className="text-2xl font-bold text-ui-dark">
            Service Diagnostics
          </h1>

          <div className="flex items-center gap-4 mt-4 sm:mt-0">
            <div className="flex items-center">
              <input
                type="checkbox"
                id="auto-refresh"
                checked={autoRefresh}
                onChange={() => setAutoRefresh(!autoRefresh)}
                className="mr-2"
              />
              <label
                htmlFor="auto-refresh"
                className="text-sm font-medium text-ui-dark"
              >
                Auto-refresh (10s)
              </label>
            </div>

            <button
              onClick={handleRefresh}
              disabled={isLoading.status || isLoading.logs}
              className="bg-primary hover:bg-primary-hover text-white px-4 py-2 rounded-md transition-colors duration-200 disabled:opacity-50"
            >
              {isLoading.status || isLoading.logs
                ? "Refreshing..."
                : "Refresh All"}
            </button>
          </div>
        </div>

        {/* Navigation tabs */}
        <div className="flex border-b border-gray-200 mb-6">
          <button
            className={`py-2 px-4 font-medium text-sm ${
              activeTab === "status"
                ? "border-b-2 border-primary text-primary"
                : "text-gray-500 hover:text-gray-700"
            }`}
            onClick={() => setActiveTab("status")}
          >
            Service Status
          </button>
          <button
            className={`py-2 px-4 font-medium text-sm ${
              activeTab === "logs"
                ? "border-b-2 border-primary text-primary"
                : "text-gray-500 hover:text-gray-700"
            }`}
            onClick={() => setActiveTab("logs")}
          >
            Logs
          </button>
        </div>

        {/* Main content based on active tab */}
        {activeTab === "status" ? renderServiceStatus() : renderLogs()}
      </div>
    </div>
  );
}

export default DockerStatus;