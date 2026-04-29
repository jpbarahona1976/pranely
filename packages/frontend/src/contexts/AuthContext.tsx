// Authentication context and hooks for frontend.
"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";

export type UserRole = "owner" | "admin" | "member" | "viewer";

export interface User {
  id: number;
  email: string;
  full_name: string | null;
  locale: string;
  is_active: boolean;
  role?: UserRole;
}

export interface Organization {
  id: number;
  name: string;
  legal_name: string | null;
  industry: string | null;
  segment: string | null;
  is_active: boolean;
}

export interface UserPermissions {
  canEdit: boolean;
  canArchive: boolean;
  canReview: boolean;
  role: UserRole;
}

interface AuthState {
  user: User | null;
  organization: Organization | null;
  token: string | null;
  isLoading: boolean;
  permissions: UserPermissions;
}

interface AuthContextType extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  register: (
    email: string,
    password: string,
    fullName: string,
    orgName: string
  ) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const TOKEN_KEY = "pranely_token";

// Map role to permissions
export function getPermissionsFromRole(role: UserRole): UserPermissions {
  const permissionsMap: Record<UserRole, UserPermissions> = {
    owner: { canEdit: true, canArchive: true, canReview: true, role: "owner" },
    admin: { canEdit: true, canArchive: true, canReview: true, role: "admin" },
    member: { canEdit: true, canArchive: false, canReview: false, role: "member" },
    viewer: { canEdit: false, canArchive: false, canReview: false, role: "viewer" },
  };
  return permissionsMap[role] || permissionsMap.viewer;
}

// Decode JWT to extract role
function decodeJWT(token: string): { sub: string; org_id: number; role?: string } | null {
  try {
    const payload = token.split(".")[1];
    const decoded = JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')));
    return decoded;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    organization: null,
    token: null,
    isLoading: true,
    permissions: getPermissionsFromRole("viewer"),
  });

  // Load token from localStorage on mount
  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (token) {
      fetchUserData(token);
    } else {
      setState((s) => ({ ...s, isLoading: false }));
    }
  }, []);

  const fetchUserData = async (token: string) => {
    try {
      // Try to fetch /me endpoint first
      try {
        const meResponse = await fetch(`${API_URL}/api/auth/me`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        
        if (meResponse.ok) {
          const userData = await meResponse.json();
          const role = (userData.role || "viewer") as UserRole;
          setState({
            user: userData.user,
            organization: userData.organization,
            token,
            isLoading: false,
            permissions: getPermissionsFromRole(role),
          });
          return;
        }
      } catch {
        // /me endpoint not available, fallback to JWT decoding
      }
      
      // Fallback: decode JWT token to get role
      const payload = decodeJWT(token);
      if (payload) {
        const role = (payload.role as UserRole) || "viewer";
        setState({
          user: { id: parseInt(payload.sub), email: "", full_name: null, locale: "es", is_active: true, role },
          organization: payload.org_id ? { id: payload.org_id, name: "", legal_name: null, industry: null, segment: null, is_active: true } : null,
          token,
          isLoading: false,
          permissions: getPermissionsFromRole(role),
        });
      } else {
        localStorage.removeItem(TOKEN_KEY);
        setState((s) => ({ ...s, isLoading: false }));
      }
    } catch {
      localStorage.removeItem(TOKEN_KEY);
      setState((s) => ({ ...s, isLoading: false }));
    }
  };

  const login = useCallback(async (email: string, password: string) => {
    const response = await fetch(`${API_URL}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail?.detail || "Login failed");
    }

    const data = await response.json();
    localStorage.setItem(TOKEN_KEY, data.token.access_token);
    
    // Extract role from login response or JWT
    const role = (data.user?.role || data.role || "viewer") as UserRole;
    
    setState({
      user: data.user,
      organization: data.organization,
      token: data.token.access_token,
      isLoading: false,
      permissions: getPermissionsFromRole(role),
    });
  }, []);

  const register = useCallback(
    async (email: string, password: string, fullName: string, orgName: string) => {
      const response = await fetch(`${API_URL}/api/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email,
          password,
          full_name: fullName || undefined,
          organization_name: orgName,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail?.detail || "Registration failed");
      }

      // Auto-login after registration
      await login(email, password);
    },
    [login]
  );

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setState({
      user: null,
      organization: null,
      token: null,
      isLoading: false,
      permissions: getPermissionsFromRole("viewer"),
    });
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
