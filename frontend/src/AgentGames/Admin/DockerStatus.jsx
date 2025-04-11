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

  // State for the different types of data
  const [overview, setOverview] = useState(null);
  const [selectedService, setSelectedService] = useState("all");
  const [logs, setLogs] = useState({});
  const [isLoading, setIsLoading] = useState({
    overview: false,
    logs: false,
  });
  const [logLines, setLogLines] = useState(100);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [activeTab, setActiveTab] = useState("overview");

  // List of available services
  const services = ["all", "api", "validator", "simulator", "postgres"];

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
    fetchOverview();
    if (selectedService) {
      fetchLogs(selectedService);
    }

    // Set up auto-refresh
    let intervalId;
    if (autoRefresh) {
      intervalId = setInterval(() => {
        fetchOverview();
        if (selectedService) {
          fetchLogs(selectedService);
        }
      }, 10000); // Refresh every 10 seconds
    }

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [navigate, autoRefresh, selectedService]);

  const fetchOverview = async () => {
    setIsLoading((prev) => ({ ...prev, overview: true }));
    try {
      const response = await fetch(`${apiUrl}/diagnostics/overview`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }

      const data = await response.json();
      if (data.status === "success") {
        setOverview(data.data);
      } else {
        toast.error("Failed to fetch system overview");
      }
    } catch (error) {
      console.error("Error fetching system overview:", error);
      toast.error(`Error: ${error.message}`);
    } finally {
      setIsLoading((prev) => ({ ...prev, overview: false }));
    }
  };

  const fetchLogs = async (service) => {
    setIsLoading((prev) => ({ ...prev, logs: true }));
    try {
      const response = await fetch(`${apiUrl}/diagnostics/logs`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          service: service,
          tail: logLines,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }

      const data = await response.json();
      if (data.status === "success") {
        setLogs(data.data.logs);
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
    fetchOverview();
    if (selectedService) {
      fetchLogs(selectedService);
    }
  };

  const formatPercentage = (value) => {
    return `${value.toFixed(2)}%`;
  };

  // Render system overview
  const renderSystemOverview = () => {
    if (!overview || !overview.system) {
      return (
        <div className="text-center p-4">Loading system information...</div>
      );
    }

    const { system } = overview;

    return (
      <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
        <h2 className="text-xl font-bold text-ui-dark mb-4">
          System Resources
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {/* CPU Usage */}
          <div className="bg-ui-lighter rounded-lg p-4">
            <div className="flex justify-between items-center mb-2">
              <span className="font-medium">CPU Usage</span>
              <span className="text-primary font-bold">
                {formatPercentage(system.cpu_percent)}
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2.5">
              <div
                className={`h-2.5 rounded-full ${
                  system.cpu_percent > 80 ? "bg-danger" : "bg-primary"
                }`}
                style={{ width: `${system.cpu_percent}%` }}
              ></div>
            </div>
          </div>

          {/* Memory Usage */}
          <div className="bg-ui-lighter rounded-lg p-4">
            <div className="flex justify-between items-center mb-2">
              <span className="font-medium">Memory Usage</span>
              <span className="text-primary font-bold">
                {formatPercentage(system.memory_percent)} (Available:{" "}
                {system.memory_available})
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2.5">
              <div
                className={`h-2.5 rounded-full ${
                  system.memory_percent > 80 ? "bg-danger" : "bg-primary"
                }`}
                style={{ width: `${system.memory_percent}%` }}
              ></div>
            </div>
          </div>

          {/* Disk Usage */}
          <div className="bg-ui-lighter rounded-lg p-4">
            <div className="flex justify-between items-center mb-2">
              <span className="font-medium">Disk Usage</span>
              <span className="text-primary font-bold">
                {formatPercentage(system.disk_percent)} (Available:{" "}
                {system.disk_available})
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2.5">
              <div
                className={`h-2.5 rounded-full ${
                  system.disk_percent > 80 ? "bg-danger" : "bg-primary"
                }`}
                style={{ width: `${system.disk_percent}%` }}
              ></div>
            </div>
          </div>

          {/* Load Average */}
          <div className="bg-ui-lighter rounded-lg p-4 md:col-span-2 lg:col-span-3">
            <div className="flex justify-between items-center mb-2">
              <span className="font-medium">Load Average</span>
              <span className="text-primary font-bold">
                1 min: {system.load_average[0].toFixed(2)} | 5 min:{" "}
                {system.load_average[1].toFixed(2)} | 15 min:{" "}
                {system.load_average[2].toFixed(2)}
              </span>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // Render service metrics
  const renderServiceMetrics = () => {
    if (!overview || !overview.resources) {
      return <div className="text-center p-4">Loading service metrics...</div>;
    }

    const { resources, statuses } = overview;

    return (
      <div className="bg-white rounded-lg shadow-lg p-6 mb-6 overflow-x-auto">
        <h2 className="text-xl font-bold text-ui-dark mb-4">Services</h2>
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-ui-lighter">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-ui-dark uppercase tracking-wider">
                Service
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-ui-dark uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-ui-dark uppercase tracking-wider">
                Health
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-ui-dark uppercase tracking-wider">
                CPU
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-ui-dark uppercase tracking-wider">
                Memory
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-ui-dark uppercase tracking-wider">
                Network I/O
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-ui-dark uppercase tracking-wider">
                Disk I/O
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-ui-dark uppercase tracking-wider">
                Uptime
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {Object.keys(resources).map((service) => {
              const resource = resources[service];
              const status = statuses[service];

              return (
                <tr key={service} className="hover:bg-ui-lightest">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-ui-dark">
                    {service}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-ui">
                    <span
                      className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full 
                                            ${
                                              resource.status === "running"
                                                ? "bg-green-100 text-green-800"
                                                : "bg-red-100 text-red-800"
                                            }`}
                    >
                      {resource.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-ui">
                    <span
                      className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full 
                                            ${
                                              status && status.is_healthy
                                                ? "bg-green-100 text-green-800"
                                                : "bg-red-100 text-red-800"
                                            }`}
                    >
                      {status
                        ? status.is_healthy
                          ? "Healthy"
                          : "Unhealthy"
                        : "Unknown"}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-ui">
                    {formatPercentage(resource.cpu_percent)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-ui">
                    {resource.memory_usage} (
                    {formatPercentage(resource.memory_percent)})
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-ui">
                    ↓ {resource.network_io.rx} / ↑ {resource.network_io.tx}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-ui">
                    ↓ {resource.disk_io.read} / ↑ {resource.disk_io.write}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-ui">
                    {resource.uptime}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
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
                <option value={50}>50</option>
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

        {selectedService === "all" ? (
          // Render logs for all services
          <div className="space-y-4">
            {Object.keys(logs).map((service) => (
              <div key={service} className="border rounded-lg overflow-hidden">
                <div className="bg-ui-lighter px-4 py-2 font-medium">
                  {service}
                </div>
                <div className="bg-ui-dark rounded-b-lg p-4 overflow-x-auto h-64">
                  <pre className="text-white font-mono text-sm whitespace-pre-wrap">
                    {logs[service] || "No logs available"}
                  </pre>
                </div>
              </div>
            ))}
          </div>
        ) : (
          // Render logs for selected service
          <div className="bg-ui-dark rounded-lg p-4 overflow-x-auto h-96">
            <pre className="text-white font-mono text-sm whitespace-pre-wrap">
              {logs[selectedService] || "No logs available"}
            </pre>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-ui-lighter pt-20 px-6 pb-8">
      <div className="max-w-[1800px] mx-auto">
        {/* Header with controls */}
        <div className="flex flex-wrap justify-between items-center mb-6">
          <h1 className="text-2xl font-bold text-ui-dark">
            System Diagnostics
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
              disabled={isLoading.overview}
              className="bg-primary hover:bg-primary-hover text-white px-4 py-2 rounded-md transition-colors duration-200 disabled:opacity-50"
            >
              {isLoading.overview ? "Refreshing..." : "Refresh All"}
            </button>
          </div>
        </div>

        {/* Navigation tabs */}
        <div className="flex border-b border-gray-200 mb-6">
          <button
            className={`py-2 px-4 font-medium text-sm 
                            ${
                              activeTab === "overview"
                                ? "border-b-2 border-primary text-primary"
                                : "text-gray-500 hover:text-gray-700"
                            }`}
            onClick={() => setActiveTab("overview")}
          >
            Overview
          </button>
          <button
            className={`py-2 px-4 font-medium text-sm 
                            ${
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
        {activeTab === "overview" ? (
          <>
            {renderSystemOverview()}
            {renderServiceMetrics()}
          </>
        ) : (
          renderLogs()
        )}
      </div>
    </div>
  );
}

export default DockerStatus;