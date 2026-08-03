/**
 * Profile Page
 * =============
 * Displays user profile information with inline editing for name and phone.
 * Protected route — requires authentication.
 */

import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { useAuth } from "../hooks/useAuth";
import { getProfile, updateProfile } from "../services/authService";

export default function Profile() {
  const { refreshUser } = useAuth();
  const [profile, setProfile] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState({ type: "", text: "" });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm();

  // Fetch profile on mount
  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const response = await getProfile();
        setProfile(response.data);
        reset({
          full_name: response.data.full_name,
          phone: response.data.phone || "",
        });
      } catch {
        setMessage({ type: "error", text: "Failed to load profile." });
      } finally {
        setIsLoading(false);
      }
    };
    fetchProfile();
  }, [reset]);

  const onSubmit = async (data) => {
    setIsSaving(true);
    setMessage({ type: "", text: "" });
    try {
      const response = await updateProfile({
        full_name: data.full_name,
        phone: data.phone || null,
      });
      setProfile(response.data);
      await refreshUser();
      setIsEditing(false);
      setMessage({ type: "success", text: "Profile updated successfully!" });
      setTimeout(() => setMessage({ type: "", text: "" }), 3000);
    } catch (err) {
      setMessage({
        type: "error",
        text: err.response?.data?.detail || "Failed to update profile.",
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    reset({
      full_name: profile.full_name,
      phone: profile.phone || "",
    });
    setIsEditing(false);
    setMessage({ type: "", text: "" });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="w-10 h-10 border-4 border-violet-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const roleName =
    typeof profile?.role === "object" ? profile.role.role_name : profile?.role;

  return (
    <div className="max-w-2xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Profile</h1>
        <p className="text-sm text-gray-500 mt-1">
          Manage your account information
        </p>
      </div>

      {/* Status message */}
      {message.text && (
        <div
          className={`mb-6 p-3 rounded-xl border text-sm ${
            message.type === "success"
              ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
              : "bg-red-500/10 border-red-500/20 text-red-400"
          }`}
        >
          {message.text}
        </div>
      )}

      {/* Profile Card */}
      <div className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/50 rounded-2xl overflow-hidden">
        {/* Avatar Banner */}
        <div className="h-32 bg-gradient-to-r from-violet-600/20 via-indigo-600/20 to-purple-600/20 relative">
          <div className="absolute -bottom-10 left-8">
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center text-white text-3xl font-bold shadow-xl shadow-violet-500/20 border-4 border-gray-900">
              {profile?.full_name?.charAt(0)?.toUpperCase() || "U"}
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="pt-14 px-8 pb-8">
          {/* Role Badge */}
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-lg font-semibold text-white">{profile?.full_name}</h2>
              <p className="text-sm text-gray-500">{profile?.email}</p>
            </div>
            <span className="inline-flex items-center px-3 py-1 rounded-lg bg-violet-500/10 text-violet-400 text-xs font-medium border border-violet-500/20">
              {roleName}
            </span>
          </div>

          {isEditing ? (
            /* ── Edit Mode ──────────────────────────────────── */
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <div>
                <label htmlFor="profile-name" className="block text-sm font-medium text-gray-300 mb-1.5">
                  Full Name
                </label>
                <input
                  id="profile-name"
                  type="text"
                  className={`w-full px-4 py-2.5 rounded-xl bg-gray-800/50 border text-white placeholder-gray-500 text-sm transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-violet-500/40 focus:border-violet-500/50 ${
                    errors.full_name ? "border-red-500/50" : "border-gray-700/50"
                  }`}
                  {...register("full_name", {
                    required: "Name is required",
                    minLength: { value: 2, message: "At least 2 characters" },
                  })}
                />
                {errors.full_name && (
                  <p className="mt-1 text-xs text-red-400">{errors.full_name.message}</p>
                )}
              </div>

              <div>
                <label htmlFor="profile-phone" className="block text-sm font-medium text-gray-300 mb-1.5">
                  Phone
                </label>
                <input
                  id="profile-phone"
                  type="tel"
                  className={`w-full px-4 py-2.5 rounded-xl bg-gray-800/50 border text-white placeholder-gray-500 text-sm transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-violet-500/40 focus:border-violet-500/50 ${
                    errors.phone ? "border-red-500/50" : "border-gray-700/50"
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

              <div className="flex gap-3 pt-2">
                <button
                  type="submit"
                  disabled={isSaving}
                  className="px-5 py-2 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 text-white text-sm font-semibold shadow-lg shadow-violet-500/25 hover:shadow-violet-500/40 transition-all duration-200 disabled:opacity-50"
                >
                  {isSaving ? "Saving..." : "Save Changes"}
                </button>
                <button
                  type="button"
                  onClick={handleCancel}
                  className="px-5 py-2 rounded-xl bg-gray-800/50 border border-gray-700/50 text-gray-400 text-sm font-medium hover:text-white hover:border-gray-600 transition-all duration-200"
                >
                  Cancel
                </button>
              </div>
            </form>
          ) : (
            /* ── View Mode ──────────────────────────────────── */
            <div className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <InfoField label="Full Name" value={profile?.full_name} />
                <InfoField label="Email" value={profile?.email} />
                <InfoField label="Phone" value={profile?.phone || "Not provided"} />
                <InfoField label="Role" value={roleName} />
                <InfoField
                  label="Status"
                  value={profile?.is_active ? "Active" : "Disabled"}
                  valueColor={profile?.is_active ? "text-emerald-400" : "text-red-400"}
                />
                <InfoField
                  label="Member Since"
                  value={new Date(profile?.created_at).toLocaleDateString("en-US", {
                    year: "numeric",
                    month: "long",
                    day: "numeric",
                  })}
                />
              </div>

              <div className="pt-4">
                <button
                  onClick={() => setIsEditing(true)}
                  className="px-5 py-2 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 text-white text-sm font-semibold shadow-lg shadow-violet-500/25 hover:shadow-violet-500/40 transition-all duration-200"
                >
                  Edit Profile
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/** Reusable info display field */
function InfoField({ label, value, valueColor = "text-white" }) {
  return (
    <div className="p-3 rounded-xl bg-gray-800/30 border border-gray-800/50">
      <p className="text-[11px] text-gray-500 uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-sm font-medium ${valueColor}`}>{value}</p>
    </div>
  );
}
