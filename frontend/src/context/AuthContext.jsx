import { createContext, useContext, useState, useEffect } from "react";
import api from "../api/axios";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    const savedUser = localStorage.getItem("auth_user");
    if (token && savedUser) {
      try {
        setUser(JSON.parse(savedUser));
      } catch {
        localStorage.removeItem("auth_user");
      }
    }
    setLoading(false);
  }, []);

  const login = async (email, password) => {
    const response = await api.post("/api/login/", { email, password });
    const data = response.data;

    // Admin OTP required — store pending details and signal the caller
    if (data.status === "ADMIN_OTP_REQUIRED") {
      localStorage.setItem("pending_admin_email", email);
      if (data.admin_id) localStorage.setItem("pending_admin_id", data.admin_id);
      throw new Error("OTP_REQUIRED");
    }

    // Support both access_token (backend) and access (standard JWT) field names
    const accessToken = data.access_token || data.access;
    const refreshToken = data.refresh_token || data.refresh;
    const userData = data.user || { email, role: data.role || "user" };

    localStorage.setItem("access_token", accessToken);
    localStorage.setItem("refresh_token", refreshToken);
    localStorage.setItem("auth_user", JSON.stringify(userData));
    if (userData.role === "admin" || userData.role === "superadmin") {
      localStorage.setItem("admin_user", JSON.stringify(userData));
    }
    setUser(userData);
    return userData;
  };

  const register = async (username, email, password) => {
    const response = await api.post("/api/register/", {
      username,
      email,
      password,
      confirm_password: password,
    });
    const data = response.data;

    const accessToken = data.access_token || data.access;
    const refreshToken = data.refresh_token || data.refresh;
    const userData = data.user || { email, role: "user" };

    localStorage.setItem("access_token", accessToken);
    localStorage.setItem("refresh_token", refreshToken);
    localStorage.setItem("auth_user", JSON.stringify(userData));
    setUser(userData);
    return { userData, redirect: data.redirect };
  };

  const loginWithOTP = async (email, otpCode) => {
    const response = await api.post("/api/verify-otp/", {
      email,
      otp_code: otpCode,
    });
    const data = response.data;

    const accessToken = data.access_token || data.access;
    const refreshToken = data.refresh_token || data.refresh;
    const userData = data.user || { email, role: "admin" };

    localStorage.setItem("access_token", accessToken);
    localStorage.setItem("refresh_token", refreshToken);
    localStorage.setItem("auth_user", JSON.stringify(userData));
    localStorage.setItem("admin_user", JSON.stringify(userData));
    localStorage.removeItem("pending_admin_email");
    localStorage.removeItem("pending_admin_id");
    setUser(userData);
    return userData;
  };

  const logout = () => {
    // Clear auth state immediately so the UI (cart, wishlist, navbar) updates
    // without waiting for the network. The backend call runs in the background
    // to blacklist the refresh token — its result doesn't affect the UI.
    const refresh = localStorage.getItem("refresh_token");
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("auth_user");
    localStorage.removeItem("admin_user");
    localStorage.removeItem("pending_admin_email");
    localStorage.removeItem("pending_admin_id");
    setUser(null);

    // Fire-and-forget: invalidate the refresh token on the backend
    if (refresh) {
      api.post("/api/logout/", { refresh }).catch(() => {});
    }
  };

  const isAdmin = user?.role === "admin" || user?.role === "superadmin";
  const isUser = user?.role === "user" || !user?.role;

  return (
    <AuthContext.Provider value={{ user, login, register, loginWithOTP, logout, loading, isAdmin, isUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
};
