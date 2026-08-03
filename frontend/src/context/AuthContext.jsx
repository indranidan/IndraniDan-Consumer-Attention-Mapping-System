/**
 * Authentication Context
 * =======================
 * React Context that manages global auth state:
 * - Current user info
 * - Login/logout functions
 * - Loading state
 * - Token persistence in localStorage
 */

import { createContext, useState, useEffect, useCallback } from "react";
import { loginUser, logoutUser, getProfile } from "../services/authService";

export const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  /**
   * Initialize auth state from localStorage on mount.
   * If a token exists, fetch the current user's profile.
   */
  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem("access_token");
      const storedUser = localStorage.getItem("user");

      if (token && storedUser) {
        try {
          // Verify token is still valid by fetching profile
          const response = await getProfile();
          const userData = response.data;
          setUser(userData);
          localStorage.setItem("user", JSON.stringify(userData));
        } catch {
          // Token expired or invalid — clear everything
          localStorage.removeItem("access_token");
          localStorage.removeItem("user");
          setUser(null);
        }
      }
      setLoading(false);
    };

    initAuth();
  }, []);

  /**
   * Log in with email and password.
   * Stores token and user in localStorage.
   */
  const login = useCallback(async (email, password) => {
    setError(null);
    try {
      const response = await loginUser({ email, password });
      const { access_token, user: userData } = response.data;

      localStorage.setItem("access_token", access_token);
      localStorage.setItem("user", JSON.stringify(userData));
      setUser(userData);

      return userData;
    } catch (err) {
      const message =
        err.response?.data?.detail || "Login failed. Please try again.";
      setError(message);
      throw err;
    }
  }, []);

  /**
   * Handle Google OAuth callback.
   * Called after Google redirects back with token params.
   */
  const handleGoogleCallback = useCallback((params) => {
    const { access_token, user_name, user_email, user_role } = params;

    if (access_token) {
      const userData = {
        full_name: user_name,
        email: user_email,
        role: user_role,
      };

      localStorage.setItem("access_token", access_token);
      localStorage.setItem("user", JSON.stringify(userData));
      setUser(userData);
    }
  }, []);

  /**
   * Log out: clear localStorage and reset state.
   */
  const logout = useCallback(async () => {
    try {
      await logoutUser();
    } catch {
      // Server logout is best-effort; always clear local state
    } finally {
      localStorage.removeItem("access_token");
      localStorage.removeItem("user");
      setUser(null);
    }
  }, []);

  /**
   * Refresh user data from the API.
   */
  const refreshUser = useCallback(async () => {
    try {
      const response = await getProfile();
      const userData = response.data;
      setUser(userData);
      localStorage.setItem("user", JSON.stringify(userData));
      return userData;
    } catch (err) {
      throw err;
    }
  }, []);

  const value = {
    user,
    loading,
    error,
    login,
    logout,
    handleGoogleCallback,
    refreshUser,
    isAuthenticated: !!user,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}
