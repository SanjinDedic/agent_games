import '../../css/App.css';
import '../User/css/login.css';
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
      // Redirect to the home page if not authenticated
      navigate('/Admin');
    }
  }, [navigate, isAuthenticated, currentUser]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setAdmin(prev => ({
      ...prev,
      [name]: value,
    }));
    setErrorMessage(''); // Clear error message when user starts typing
  };

  const handleSubmit = async (e) => {
    e.preventDefault(); // Prevent default form submission

    if (!admin.name.trim() || !admin.password.trim()) {
      setShake(true);
      setTimeout(() => setShake(false), 1000);
      setErrorMessage('Please enter all the fields');
      return;
    }

    try {
      const response = await fetch(`${apiUrl}/admin_login`, {
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
    <div className="login-main-container">
      <div className="login-container" id="login-container">
        <form onSubmit={handleSubmit}>
          <div className="input-group">
            <h1>Username:</h1>
            <input
              type="text"
              id="admin_name"
              name="name"
              value={admin.name}
              onChange={handleChange}
              className={shake ? 'shake' : ''}
            />
          </div>
          <div className="input-group">
            <h1>Password:</h1>
            <input
              type="password"
              id="admin_password"
              name="password"
              value={admin.password}
              onChange={handleChange}
              className={shake ? 'shake' : ''}
            />
          </div>
          <button type="submit" className='submit-button'>Login</button>
          {errorMessage && <p className="error-message">{errorMessage}</p>}
        </form>
      </div>
    </div>
  );
}

export default Admin;