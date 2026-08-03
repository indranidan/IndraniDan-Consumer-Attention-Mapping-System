/**
 * Login Page
 * ===========
 * Email/password login form with Google OAuth button.
 * Uses React Hook Form for validation.
 */

import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { useAuth } from "../hooks/useAuth";
import { getGoogleLoginUrl } from "../services/authService";
import AuthLayout from "../components/layouts/AuthLayout";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [serverError, setServerError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    defaultValues: { email: "", password: "" },
  });

  const onSubmit = async (data) => {
    setIsLoading(true);
    setServerError("");
    try {
      await login(data.email, data.password);
      navigate("/dashboard");
    } catch (err) {
      setServerError(
        err.response?.data?.detail || "Login failed. Please try again."
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleLogin = () => {
    window.location.href = getGoogleLoginUrl();
  };

  return (
    <AuthLayout>
      <div>
        <h2 className="text-xl font-semibold text-white mb-1">Welcome back</h2>
        <p className="text-sm text-gray-500 mb-6">
          Sign in to your account to continue
        </p>

        {/* Server error */}
        {serverError && (
          <div className="mb-4 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
            {serverError}
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* Email */}
          <div>
            <label
              htmlFor="login-email"
              className="block text-sm font-medium text-gray-300 mb-1.5"
            >
              Email
            </label>
            <input
              id="login-email"
              type="email"
              autoComplete="email"
              className={`w-full px-4 py-2.5 rounded-xl bg-gray-800/50 border text-white placeholder-gray-500 text-sm transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-violet-500/40 focus:border-violet-500/50 ${
                errors.email
                  ? "border-red-500/50"
                  : "border-gray-700/50 hover:border-gray-600"
              }`}
              placeholder="you@example.com"
              {...register("email", {
                required: "Email is required",
                pattern: {
                  value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
                  message: "Enter a valid email address",
                },
              })}
            />
            {errors.email && (
              <p className="mt-1 text-xs text-red-400">{errors.email.message}</p>
            )}
          </div>

          {/* Password */}
          <div>
            <label
              htmlFor="login-password"
              className="block text-sm font-medium text-gray-300 mb-1.5"
            >
              Password
            </label>
            <input
              id="login-password"
              type="password"
              autoComplete="current-password"
              className={`w-full px-4 py-2.5 rounded-xl bg-gray-800/50 border text-white placeholder-gray-500 text-sm transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-violet-500/40 focus:border-violet-500/50 ${
                errors.password
                  ? "border-red-500/50"
                  : "border-gray-700/50 hover:border-gray-600"
              }`}
              placeholder="••••••••"
              {...register("password", {
                required: "Password is required",
              })}
            />
            {errors.password && (
              <p className="mt-1 text-xs text-red-400">{errors.password.message}</p>
            )}
          </div>

          {/* Submit */}
          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 text-white text-sm font-semibold shadow-lg shadow-violet-500/25 hover:shadow-violet-500/40 hover:from-violet-500 hover:to-indigo-500 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Signing in...
              </span>
            ) : (
              "Sign In"
            )}
          </button>
        </form>

        {/* Divider */}
        <div className="relative my-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-gray-800" />
          </div>
          <div className="relative flex justify-center text-xs">
            <span className="px-3 bg-gray-900/60 text-gray-500">or continue with</span>
          </div>
        </div>

        {/* Google OAuth */}
        <button
          onClick={handleGoogleLogin}
          type="button"
          className="w-full flex items-center justify-center gap-3 py-2.5 px-4 rounded-xl bg-gray-800/50 border border-gray-700/50 text-gray-300 text-sm font-medium hover:bg-gray-800 hover:border-gray-600 transition-all duration-200"
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24">
            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" />
            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
          </svg>
          Sign in with Google
        </button>

        {/* Register link */}
        <p className="text-center text-sm text-gray-500 mt-6">
          Don't have an account?{" "}
          <Link
            to="/register"
            className="text-violet-400 hover:text-violet-300 font-medium transition-colors"
          >
            Create one
          </Link>
        </p>
      </div>
    </AuthLayout>
  );
}
