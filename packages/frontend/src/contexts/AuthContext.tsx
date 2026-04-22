"""Authentication context and hooks for frontend."""
"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";

interface User {
  id: number;
  email: string;
  full_name: string | null;
  locale: string;
  is_active: boolean;
}

interface Organization {
  id: number;
  name: string;
  legal_name: string | null;
  industry: string | null;
  segment: string | null;
  is_active: boolean;
}

interface AuthState {
  user: User | null;
  organization: Organization | null;
  token: string | null;
  isLoading: boolean;
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

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    organization: null,
    token: null,
    isLoading: true,
  });

  // Load token from localStorage on mount
  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (token) {
      // Validate token and get user data
      fetchUserData(token);
    } else {
      setState((s) => ({ ...s, isLoading: false }));
    }
  }, []);

  const fetchUserData = async (token: string) => {
    try {
      // For now, we'll decode the token to get basic info
      // In a real app, you'd have a /me endpoint
      const payload = JSON.parse(atob(token.split(".")[1]));
      setState({
        user: { id: parseInt(payload.sub), email: "", full_name: null, locale: "es", is_active: true },
        organization: payload.org_id ? { id: payload.org_id, name: "", legal_name: null, industry: null, segment: null, is_active: true } : null,
        token,
        isLoading: false,
      });
    } catch {
      localStorage.removeItem(TOKEN_KEY);
      setState({ user: null, organization: null, token: null, isLoading: false });
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
    setState({
      user: data.user,
      organization: data.organization,
      token: data.token.access_token,
      isLoading: false,
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
    setState({ user: null, organization: null, token: null, isLoading: false });
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