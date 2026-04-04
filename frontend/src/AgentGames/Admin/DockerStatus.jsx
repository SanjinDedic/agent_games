import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { toast } from 'react-toastify';
import { checkTokenExpiry } from '../../slices/authSlice';
import { authFetch } from '../../utils/authFetch';

function DockerStatus() {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const accessToken = useSelector((state) => state.auth.token);
  const currentUser = useSelector((state) => state.auth.currentUser);
  const isAuthenticated = useSelector((state) => state.auth.isAuthenticated);

  const [serviceStatus, setServiceStatus] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(false);

  // Auth guard (mount-only to avoid loop on logout)
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Fetch status and auto-refresh
  useEffect(() => {
    fetchServiceStatus();

    let intervalId;
    if (autoRefresh) {
      intervalId = setInterval(() => {
        fetchServiceStatus();
      }, 10000);
    }

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [autoRefresh]);

  const fetchServiceStatus = async () => {
    setIsLoading(true);
    try {
      const response = await authFetch(`${apiUrl}/diagnostics/status`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }

      const data = await response.json();
      if (data.status === "success") {
        setServiceStatus({
          web: {
            name: "web",
            status: "running",
            health: "Service web is healthy (HTTP 200)",
            is_healthy: true,
          },
          ...data.data.statuses,
        });
      } else {
        toast.error("Failed to fetch service status");
      }
    } catch (error) {
      console.error("Error fetching service status:", error);
      toast.error(`Error: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const renderServiceStatus = () => {
    if (!serviceStatus) {
      return <div className="text-center p-4">Loading service status...</div>;
    }

    return (
      <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
        <h2 className="text-xl font-bold text-ui-dark mb-4">Service Status</h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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

  return (
    <div className="min-h-screen bg-ui-lighter pt-20 px-6 pb-8">
      <div className="max-w-6xl mx-auto">
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
              onClick={fetchServiceStatus}
              disabled={isLoading}
              className="bg-primary hover:bg-primary-hover text-white px-4 py-2 rounded-md transition-colors duration-200 disabled:opacity-50"
            >
              {isLoading ? "Refreshing..." : "Refresh All"}
            </button>
          </div>
        </div>

        {renderServiceStatus()}
      </div>
    </div>
  );
}

export default DockerStatus;
