/**
 * useAuth Hook
 * ==============
 * Convenience hook for accessing the AuthContext.
 * Throws an error if used outside of AuthProvider.
 */

import { useContext } from "react";
import { AuthContext } from "../context/AuthContext";

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
