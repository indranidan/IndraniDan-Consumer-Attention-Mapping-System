/**
 * Role Guard Component
 * =====================
 * Wraps routes or UI elements that require specific roles.
 * Shows access denied message if the user's role is not allowed.
 *
 * Usage:
 *   <RoleGuard allowedRoles={["Administrator", "Store Manager"]}>
 *     <AdminPanel />
 *   </RoleGuard>
 */

import { useAuth } from "../hooks/useAuth";

export default function RoleGuard({ allowedRoles, children }) {
  const { user } = useAuth();

  // Get the user's role name — handle both object and string formats
  const userRole =
    typeof user?.role === "object" ? user.role.role_name : user?.role;

  if (!userRole || !allowedRoles.includes(userRole)) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center p-8 bg-gray-900/50 backdrop-blur-xl rounded-2xl border border-red-500/20 max-w-md">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-red-500/10 flex items-center justify-center">
            <svg className="w-8 h-8 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"
              />
            </svg>
          </div>
          <h3 className="text-xl font-semibold text-white mb-2">Access Denied</h3>
          <p className="text-gray-400 text-sm">
            You don't have permission to access this resource.
            Required role: <span className="text-violet-400 font-medium">{allowedRoles.join(", ")}</span>
          </p>
        </div>
      </div>
    );
  }

  return children;
}
