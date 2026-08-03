/**
 * Authentication Service
 * =======================
 * API calls for authentication and user management endpoints.
 * All functions return Axios promises.
 */

import api from "./api";

const AUTH_PREFIX = "/api/auth";
const USERS_PREFIX = "/api/users";

/**
 * Register a new user.
 * @param {Object} data - { full_name, email, password, phone?, role_id }
 */
export const registerUser = (data) => {
  return api.post(`${AUTH_PREFIX}/register`, data);
};

/**
 * Login with email and password.
 * @param {Object} data - { email, password }
 * @returns {Promise} - Resolves with { access_token, token_type, user }
 */
export const loginUser = (data) => {
  return api.post(`${AUTH_PREFIX}/login`, data);
};

/**
 * Logout (server acknowledgement).
 */
export const logoutUser = () => {
  return api.post(`${AUTH_PREFIX}/logout`);
};

/**
 * Get all available roles for registration.
 * @returns {Promise} - Resolves with [{ id, role_name }]
 */
export const getRoles = () => {
  return api.get(`${AUTH_PREFIX}/roles`);
};

/**
 * Get the current user's profile.
 * @returns {Promise} - Resolves with full user profile
 */
export const getProfile = () => {
  return api.get(`${USERS_PREFIX}/profile`);
};

/**
 * Update the current user's profile.
 * @param {Object} data - { full_name?, phone? }
 */
export const updateProfile = (data) => {
  return api.put(`${USERS_PREFIX}/profile`, data);
};

/**
 * Get the Google OAuth login URL.
 * Redirects the browser to Google's consent screen.
 */
export const getGoogleLoginUrl = () => {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
  return `${baseUrl}${AUTH_PREFIX}/google/login`;
};
