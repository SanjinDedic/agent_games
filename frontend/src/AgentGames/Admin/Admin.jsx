import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { login, checkTokenExpiry } from '../../slices/authSlice';
import { jwtDecode } from 'jwt-decode';


function Admin() {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const currentUser = useSelector((state) => state.auth.currentUser);
  const isAuthenticated = useSelector((state) => state.auth.isAuthenticated);
  const [admin, setAdmin] = useState({ name: '', password: '' });
  const [errorMessage, setErrorMessage] = useState('');
  const [shake, setShake] = useState(false);

  useEffect(() => {
    const tokenExpired = dispatch(checkTokenExpiry());
    if (!isAuthenticated || currentUser.role !== "admin" || tokenExpired) {
      navigate('/Admin');
    }
  }, [navigate, isAuthenticated, currentUser]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setAdmin(prev => ({
      ...prev,
      [name]: value,
    }));
    setErrorMessage('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!admin.name.trim() || !admin.password.trim()) {
      setShake(true);
      setTimeout(() => setShake(false), 1000);
      setErrorMessage('Please enter all the fields');
      return;
    }

    try {
      const response = await fetch(`${apiUrl}/auth/admin-login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ username: admin.name, password: admin.password }),
      });

      const data = await response.json();
      if (data.status === "success") {
        const decoded = jwtDecode(data.data.access_token);
        dispatch(login({ token: data.data.access_token, name: decoded.sub, role: decoded.role }));
        navigate("/AdminTeam");
      } else if (data.status === "failed") {
        setErrorMessage(data.message);
      }
    } catch (error) {
      console.error('Error:', error);
      setErrorMessage('An error occurred. Please try again.');
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen pt-16 px-4 bg-ui-lighter">
      <div className="w-full max-w-lg bg-white rounded-lg shadow-lg p-8">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <h1 className="text-2xl font-bold text-ui-dark">Username:</h1>
            <input
              type="text"
              id="admin_name"
              name="name"
              value={admin.name}
              onChange={handleChange}
              className={`w-full px-4 py-2 text-lg border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary transition-all duration-200 
                ${shake ? 'animate-shake border-danger' : 'border-ui-light focus:border-primary'}`}
            />
          </div>

          <div className="space-y-2">
            <h1 className="text-2xl font-bold text-ui-dark">Password:</h1>
            <input
              type="password"
              id="admin_password"
              name="password"
              value={admin.password}
              onChange={handleChange}
              className={`w-full px-4 py-2 text-lg border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary transition-all duration-200
                ${shake ? 'animate-shake border-danger' : 'border-ui-light focus:border-primary'}`}
            />
          </div>

          <button
            type="submit"
            className="w-full py-4 px-6 text-lg font-bold text-white bg-primary hover:bg-primary-hover rounded-lg transition-colors duration-200"
          >
            Login
          </button>

          {errorMessage && (
            <p className="text-lg text-danger text-center">{errorMessage}</p>
          )}
        </form>
      </div>
    </div>
  );
}

export default Admin;