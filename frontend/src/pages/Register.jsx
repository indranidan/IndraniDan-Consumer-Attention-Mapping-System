/**
 * Register Page
 * ==============
 * Registration form with role dropdown and strong password validation.
 * Fetches available roles from the API on mount.
 */

import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { registerUser, getRoles } from "../services/authService";
import AuthLayout from "../components/layouts/AuthLayout";

export default function Register() {
  const navigate = useNavigate();
  const [roles, setRoles] = useState([]);
  const [serverError, setServerError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    defaultValues: {
      full_name: "",
      email: "",
      password: "",
      phone: "",
      role_id: "",
    },
  });

  // Fetch roles on mount
  useEffect(() => {
    const fetchRoles = async () => {
      try {
        const response = await getRoles();
        setRoles(response.data);
      } catch {
        setServerError("Failed to load roles. Please refresh the page.");
      }
    };
    fetchRoles();
  }, []);

  const onSubmit = async (data) => {
    setIsLoading(true);
    setServerError("");
    try {
      const payload = {
        ...data,
        phone: data.phone || null,
      };
      await registerUser(payload);
      setSuccess(true);
      setTimeout(() => navigate("/login"), 2000);
    } catch (err) {
      setServerError(
        err.response?.data?.detail || "Registration failed. Please try again."
      );
    } finally {
      setIsLoading(false);
    }
  };

  if (success) {
    return (
      <AuthLayout>
        <div className="text-center py-8">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-emerald-500/10 flex items-center justify-center">
            <svg className="w-8 h-8 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h3 className="text-xl font-semibold text-white mb-2">Account Created!</h3>
          <p className="text-sm text-gray-400">
            Redirecting you to login...
          </p>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout>
      <div>
        <h2 className="text-xl font-semibold text-white mb-1">Create account</h2>
        <p className="text-sm text-gray-500 mb-6">
          Fill in your details to get started
        </p>

        {serverError && (
          <div className="mb-4 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
            {serverError}
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* Full Name */}
          <div>
            <label htmlFor="reg-name" className="block text-sm font-medium text-gray-300 mb-1.5">
              Full Name
            </label>
            <input
              id="reg-name"
              type="text"
              className={`w-full px-4 py-2.5 rounded-xl bg-gray-800/50 border text-white placeholder-gray-500 text-sm transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-violet-500/40 focus:border-violet-500/50 ${
                errors.full_name ? "border-red-500/50" : "border-gray-700/50 hover:border-gray-600"
              }`}
              placeholder="John Doe"
              {...register("full_name", {
                required: "Full name is required",
                minLength: { value: 2, message: "Name must be at least 2 characters" },
              })}
            />
            {errors.full_name && (
              <p className="mt-1 text-xs text-red-400">{errors.full_name.message}</p>
            )}
          </div>

          {/* Email */}
          <div>
            <label htmlFor="reg-email" className="block text-sm font-medium text-gray-300 mb-1.5">
              Email
            </label>
            <input
              id="reg-email"
              type="email"
              autoComplete="email"
              className={`w-full px-4 py-2.5 rounded-xl bg-gray-800/50 border text-white placeholder-gray-500 text-sm transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-violet-500/40 focus:border-violet-500/50 ${
                errors.email ? "border-red-500/50" : "border-gray-700/50 hover:border-gray-600"
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
            <label htmlFor="reg-password" className="block text-sm font-medium text-gray-300 mb-1.5">
              Password
            </label>
            <input
              id="reg-password"
              type="password"
              autoComplete="new-password"
              className={`w-full px-4 py-2.5 rounded-xl bg-gray-800/50 border text-white placeholder-gray-500 text-sm transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-violet-500/40 focus:border-violet-500/50 ${
                errors.password ? "border-red-500/50" : "border-gray-700/50 hover:border-gray-600"
              }`}
              placeholder="Min 8 chars, upper, lower, digit, special"
              {...register("password", {
                required: "Password is required",
                minLength: { value: 8, message: "Minimum 8 characters" },
                validate: {
                  hasUpper: (v) => /[A-Z]/.test(v) || "Must include an uppercase letter",
                  hasLower: (v) => /[a-z]/.test(v) || "Must include a lowercase letter",
                  hasDigit: (v) => /\d/.test(v) || "Must include a digit",
                  hasSpecial: (v) =>
                    /[!@#$%^&*(),.?":{}|<>_\-+=[\]\\/~`]/.test(v) ||
                    "Must include a special character",
                },
              })}
            />
            {errors.password && (
              <p className="mt-1 text-xs text-red-400">{errors.password.message}</p>
            )}
          </div>

          {/* Phone */}
          <div>
            <label htmlFor="reg-phone" className="block text-sm font-medium text-gray-300 mb-1.5">
              Phone <span className="text-gray-600">(optional)</span>
            </label>
            <input
              id="reg-phone"
              type="tel"
              className={`w-full px-4 py-2.5 rounded-xl bg-gray-800/50 border text-white placeholder-gray-500 text-sm transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-violet-500/40 focus:border-violet-500/50 ${
                errors.phone ? "border-red-500/50" : "border-gray-700/50 hover:border-gray-600"
              }`}
              placeholder="+1234567890"
              {...register("phone", {
                pattern: {
                  value: /^\+?[\d\s\-()]{7,20}$/,
                  message: "Invalid phone format",
                },
              })}
            />
            {errors.phone && (
              <p className="mt-1 text-xs text-red-400">{errors.phone.message}</p>
            )}
          </div>

          {/* Role */}
          <div>
            <label htmlFor="reg-role" className="block text-sm font-medium text-gray-300 mb-1.5">
              Role
            </label>
            <select
              id="reg-role"
              className={`w-full px-4 py-2.5 rounded-xl bg-gray-800/50 border text-white text-sm transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-violet-500/40 focus:border-violet-500/50 appearance-none cursor-pointer ${
                errors.role_id ? "border-red-500/50" : "border-gray-700/50 hover:border-gray-600"
              }`}
              {...register("role_id", { required: "Please select a role" })}
            >
              <option value="" className="bg-gray-900 text-gray-500">
                Select a role...
              </option>
              {roles.map((role) => (
                <option key={role.id} value={role.id} className="bg-gray-900">
                  {role.role_name}
                </option>
              ))}
            </select>
            {errors.role_id && (
              <p className="mt-1 text-xs text-red-400">{errors.role_id.message}</p>
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
                Creating account...
              </span>
            ) : (
              "Create Account"
            )}
          </button>
        </form>

        {/* Login link */}
        <p className="text-center text-sm text-gray-500 mt-6">
          Already have an account?{" "}
          <Link
            to="/login"
            className="text-violet-400 hover:text-violet-300 font-medium transition-colors"
          >
            Sign in
          </Link>
        </p>
      </div>
    </AuthLayout>
  );
}
