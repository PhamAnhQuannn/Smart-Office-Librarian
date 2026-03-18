"use client";

import { useCallback, useEffect, useState } from "react";

import {
  clearToken,
  currentUser,
  getToken,
  hasRole,
  isAuthenticated,
  isTokenExpired,
  setToken,
} from "../lib/auth";
import type { AuthUser, UserRole } from "../types/user";

interface UseAuthResult {
  user: AuthUser | null;
  isLoggedIn: boolean;
  isAdmin: boolean;
  token: string | null;
  login: (jwt: string) => void;
  logout: () => void;
  checkRole: (role: UserRole) => boolean;
}

export function useAuth(): UseAuthResult {
  const [user, setUser] = useState<AuthUser | null>(() => currentUser());

  // Expire-check on mount and visibility change
  useEffect(() => {
    if (isAuthenticated() && isTokenExpired()) {
      clearToken();
      setUser(null);
    }
  }, []);

  const login = useCallback((jwt: string) => {
    setToken(jwt);
    setUser(currentUser());
  }, []);

  const logout = useCallback(() => {
    clearToken();
    setUser(null);
  }, []);

  const checkRole = useCallback((role: UserRole) => hasRole(role), []);

  return {
    user,
    isLoggedIn: user !== null,
    isAdmin: user?.role === "admin",
    token: getToken(),
    login,
    logout,
    checkRole,
  };
}
