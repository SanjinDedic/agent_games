import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import {
  selectCurrentUser,
  selectIsAuthenticated,
  selectIsTokenExpired,
} from '../../../slices/authSlice';
import { sessionExpired } from '../../../middleware/authErrorMiddleware';

// requiredRole: a single role string, or an array when several roles may
// enter (e.g. ["admin", "institution"] for the tutorial preview).
const roleAllowed = (requiredRole, role) => {
  if (!requiredRole) return true;
  return Array.isArray(requiredRole)
    ? requiredRole.includes(role)
    : role === requiredRole;
};

const AuthProtection = ({
  children,
  requiredRole,
  redirectTo,
}) => {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const currentUser = useSelector(selectCurrentUser);
  const isAuthenticated = useSelector(selectIsAuthenticated);
  const tokenExpired = useSelector(selectIsTokenExpired);

  useEffect(() => {
    if (tokenExpired) {
      dispatch(sessionExpired());
      return;
    }
    if (!isAuthenticated || !roleAllowed(requiredRole, currentUser.role)) {
      navigate(redirectTo);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!isAuthenticated || !roleAllowed(requiredRole, currentUser.role)) {
    return null;
  }

  return <>{children}</>;
};

export default AuthProtection;