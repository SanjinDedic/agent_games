import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import {
  selectCurrentUser,
  selectIsAuthenticated,
  selectIsTokenExpired,
} from '../../../slices/authSlice';
import { sessionExpired } from '../../../middleware/authErrorMiddleware';

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
    if (!isAuthenticated || (requiredRole && currentUser.role !== requiredRole)) {
      navigate(redirectTo);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!isAuthenticated || (requiredRole && currentUser.role !== requiredRole)) {
    return null;
  }

  return <>{children}</>;
};

export default AuthProtection;