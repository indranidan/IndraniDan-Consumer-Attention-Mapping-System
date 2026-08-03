/**
 * App Component
 * ==============
 * Root component with React Router configuration.
 * Defines public routes (login, register) and protected routes
 * (dashboard, profile, store management) wrapped in AuthProvider.
 */

import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import AppLayout from "./components/layouts/AppLayout";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import Profile from "./pages/Profile";
import GoogleCallback from "./pages/GoogleCallback";
import Stores from "./pages/Stores";
import StoreDetails from "./pages/StoreDetails";
import Zones from "./pages/Zones";
import Shelves from "./pages/Shelves";
import Products from "./pages/Products";
import Cameras from "./pages/Cameras";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* ── Public Routes ─────────────────────────────── */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/auth/google/callback" element={<GoogleCallback />} />

          {/* ── Protected Routes ──────────────────────────── */}
          <Route element={<ProtectedRoute />}>
            <Route element={<AppLayout />}>
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/profile" element={<Profile />} />
              <Route path="/stores" element={<Stores />} />
              <Route path="/stores/:id" element={<StoreDetails />} />
              <Route path="/zones" element={<Zones />} />
              <Route path="/shelves" element={<Shelves />} />
              <Route path="/products" element={<Products />} />
              <Route path="/cameras" element={<Cameras />} />
            </Route>
          </Route>

          {/* ── Catch-all redirect ────────────────────────── */}
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
