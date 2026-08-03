/**
 * Google OAuth Callback Handler
 * ===============================
 * Receives the token and user info from the Google OAuth redirect,
 * stores them via AuthContext, and redirects to the dashboard.
 */

import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

export default function GoogleCallback() {
  const [searchParams] = useSearchParams();
  const { handleGoogleCallback } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    const accessToken = searchParams.get("access_token");
    const userName = searchParams.get("user_name");
    const userEmail = searchParams.get("user_email");
    const userRole = searchParams.get("user_role");

    if (accessToken) {
      handleGoogleCallback({
        access_token: accessToken,
        user_name: userName,
        user_email: userEmail,
        user_role: userRole,
      });
      navigate("/dashboard", { replace: true });
    } else {
      navigate("/login", { replace: true });
    }
  }, [searchParams, handleGoogleCallback, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950">
      <div className="flex flex-col items-center gap-4">
        <div className="w-12 h-12 border-4 border-violet-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-gray-400 text-sm">Completing sign in...</p>
      </div>
    </div>
  );
}
