// src/AgentGames/Shared/Auth/AuthProtection.jsx
import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import {
  checkTokenExpiry,
  selectCurrentUser,
  selectIsAuthenticated,
} from '../../../slices/authSlice';

const AuthProtection = ({
  children,
  requiredRole,
  redirectTo
}) => {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const currentUser = useSelector(selectCurrentUser);
  const isAuthenticated = useSelector(selectIsAuthenticated);
  
  useEffect(() => {
    const tokenExpired = dispatch(checkTokenExpiry());
    if (!isAuthenticated || (requiredRole && currentUser.role !== requiredRole) || tokenExpired) {
      navigate(redirectTo);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // If not authenticated or wrong role, don't render children
  if (!isAuthenticated || (requiredRole && currentUser.role !== requiredRole)) {
    return null;
  }

  return <>{children}</>;
};

export default AuthProtection;