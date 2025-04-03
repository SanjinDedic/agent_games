// src/AgentGames/Shared/Auth/AuthProtection.jsx
import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { checkTokenExpiry } from '../../../slices/authSlice';

const AuthProtection = ({
  children,
  requiredRole,
  redirectTo
}) => {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const currentUser = useSelector((state) => state.auth.currentUser);
  const isAuthenticated = useSelector((state) => state.auth.isAuthenticated);
  
  useEffect(() => {
    const tokenExpired = dispatch(checkTokenExpiry());
    if (!isAuthenticated || (requiredRole && currentUser.role !== requiredRole) || tokenExpired) {
      navigate(redirectTo);
    }
  }, [navigate, dispatch, isAuthenticated, currentUser, requiredRole, redirectTo]);

  // If not authenticated or wrong role, don't render children
  if (!isAuthenticated || (requiredRole && currentUser.role !== requiredRole)) {
    return null;
  }

  return <>{children}</>;
};

export default AuthProtection;