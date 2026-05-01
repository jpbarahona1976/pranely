// Login form component - Glassmorphism style with multi-org support
"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";

interface OrganizationOption {
  org_id: number;
  org_name: string;
  role: string;
}

type LoginStep = "credentials" | "org_selection" | "loading";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function loginWithOrgDetection(email: string, password: string) {
  const response = await fetch(`${API_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    return {
      success: false,
      needsOrgSelection: false,
      error: errorData.detail?.detail || `HTTP ${response.status}`,
    };
  }

  const data = await response.json();

  // Backend signals multi-org user: returns available_orgs without token
  if (data.available_orgs && data.available_orgs.length > 0) {
    return {
      success: false,
      needsOrgSelection: true,
      availableOrgs: data.available_orgs as OrganizationOption[],
    };
  }

  // Single org: token present, login successful
  if (data.token && data.token.access_token) {
    localStorage.setItem("pranely_token", data.token.access_token);
    if (data.organization?.id) {
      localStorage.setItem("pranely_org_id", String(data.organization.id));
    }
    return { success: true };
  }

  return { success: false, error: "Respuesta inesperada del servidor" };
}

async function loginWithOrgSelection(email: string, password: string, orgId: number) {
  const response = await fetch(`${API_URL}/api/auth/login?org_id=${orgId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    return {
      success: false,
      error: errorData.detail?.detail || `HTTP ${response.status}`,
    };
  }

  const data = await response.json();

  if (data.token && data.token.access_token) {
    localStorage.setItem("pranely_token", data.token.access_token);
    if (data.organization?.id) {
      localStorage.setItem("pranely_org_id", String(data.organization.id));
    }
    return { success: true };
  }

  return { success: false, error: "No se recibio token" };
}

export function LoginForm() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [step, setStep] = useState<LoginStep>("credentials");
  const [availableOrgs, setAvailableOrgs] = useState<OrganizationOption[]>([]);
  const [storedCredentials, setStoredCredentials] = useState({ email: "", password: "" });

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      const result = await loginWithOrgDetection(email, password);

      if (result.needsOrgSelection && result.availableOrgs) {
        setAvailableOrgs(result.availableOrgs);
        setStoredCredentials({ email, password });
        setStep("org_selection");
      } else if (result.success) {
        window.location.href = "/dashboard";
      } else {
        setError(result.error || "Error al iniciar sesion");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al iniciar sesion");
    } finally {
      setIsLoading(false);
    }
  };

  const handleOrgSelect = async (org: OrganizationOption) => {
    setError("");
    setIsLoading(true);

    try {
      const result = await loginWithOrgSelection(storedCredentials.email, storedCredentials.password, org.org_id);

      if (result.success) {
        window.location.href = "/dashboard";
      } else {
        setError(result.error || "Error al iniciar sesion");
        setStep("credentials");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al iniciar sesion");
      setStep("credentials");
    } finally {
      setIsLoading(false);
    }
  };

  const handleBack = () => {
    setStep("credentials");
    setAvailableOrgs([]);
    setStoredCredentials({ email: "", password: "" });
    setError("");
  };

  // ─── Org Selection Step ────────────────────────────────────────────────────────
  if (step === "org_selection") {
    return (
      <div className="min-h-screen relative overflow-hidden flex items-center justify-center py-12 px-4">
        <div className="fixed inset-0 -z-10">
          <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900" />
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-emerald-500/20 rounded-full blur-3xl animate-pulse" />
          <div className="absolute top-1/3 right-1/4 w-80 h-80 bg-violet-500/15 rounded-full blur-3xl animate-pulse" />
        </div>

        <div className="w-full max-w-md">
          <div className="relative">
            <div className="absolute -inset-1 bg-gradient-to-r from-emerald-500/20 to-teal-500/20 rounded-3xl blur-xl opacity-50" />
            <div className="relative rounded-3xl bg-white/5 backdrop-blur-xl border border-white/10 shadow-2xl overflow-hidden p-8">
              {/* Header */}
              <div className="text-center mb-6">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-emerald-400 via-teal-500 to-emerald-600 shadow-lg shadow-emerald-500/30 mb-4">
                  <span className="text-white font-black text-2xl">P</span>
                </div>
                <h2 className="text-xl font-bold text-white mb-1">Selecciona Organizacion</h2>
                <p className="text-white/60 text-sm">
                  Tienes acceso a multiples organizaciones
                </p>
              </div>

              {/* Error display */}
              {error && (
                <div className="mb-4 p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20">
                  <p className="text-sm text-rose-300">{error}</p>
                </div>
              )}

              {/* Org list */}
              <div className="space-y-3 mb-6">
                {availableOrgs.map((org) => (
                  <button
                    key={org.org_id}
                    onClick={() => handleOrgSelect(org)}
                    disabled={isLoading}
                    className="w-full p-4 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 hover:border-emerald-500/30 transition-all disabled:opacity-50 text-left"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-white font-medium">{org.org_name}</p>
                        <p className="text-white/50 text-sm capitalize">{org.role}</p>
                      </div>
                      <div className="w-3 h-3 rounded-full bg-emerald-500" />
                    </div>
                  </button>
                ))}
              </div>

              {/* Back button */}
              <button
                onClick={handleBack}
                className="w-full text-center text-white/40 hover:text-white text-sm transition-colors py-2"
              >
                Volver al inicio de sesion
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ─── Credentials Step ─────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen relative overflow-hidden flex items-center justify-center py-12 px-4">
      <div className="fixed inset-0 -z-10">
        <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900" />
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-emerald-500/20 rounded-full blur-3xl animate-pulse" />
        <div className="absolute top-1/3 right-1/4 w-80 h-80 bg-violet-500/15 rounded-full blur-3xl animate-pulse" />
        <div className="absolute bottom-1/4 left-1/3 w-72 h-72 bg-blue-500/15 rounded-full blur-3xl animate-pulse" />
      </div>

      <div className="w-full max-w-md">
        <div className="relative">
          <div className="absolute -inset-1 bg-gradient-to-r from-emerald-500/20 to-teal-500/20 rounded-3xl blur-xl opacity-50" />
          <div className="relative rounded-3xl bg-white/5 backdrop-blur-xl border border-white/10 shadow-2xl overflow-hidden">
            {/* Header */}
            <div className="p-8 pb-0 text-center">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-emerald-400 via-teal-500 to-emerald-600 shadow-lg shadow-emerald-500/30 mb-6">
                <span className="text-white font-black text-2xl">P</span>
              </div>
              <h1 className="text-2xl font-bold text-white tracking-tight mb-2">PRANELY</h1>
              <p className="text-slate-300 text-sm mb-6">Sistema Documental Maestro</p>
            </div>

            {/* Form */}
            <form className="p-8 pt-4 space-y-5" onSubmit={handleSubmit}>
              {error && (
                <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 flex items-start gap-3">
                  <svg className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <p className="text-sm text-rose-300">{error}</p>
                </div>
              )}

              <div className="space-y-2">
                <label htmlFor="email" className="block text-sm font-medium text-white/70">
                  Correo electronico
                </label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="correo@ejemplo.com"
                  className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-white/30 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/30 transition-all duration-200"
                />
              </div>

              <div className="space-y-2">
                <label htmlFor="password" className="block text-sm font-medium text-white/70">
                  Contrasena
                </label>
                <input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-white/30 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/30 transition-all duration-200"
                />
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-3.5 px-4 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 text-white font-semibold text-sm shadow-lg shadow-emerald-500/30 hover:shadow-emerald-500/50 hover:from-emerald-400 hover:to-teal-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 flex items-center justify-center gap-2"
              >
                {isLoading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>Iniciando sesion...</span>
                  </>
                ) : (
                  <span>Iniciar sesion</span>
                )}
              </button>

              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-white/10" />
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="px-3 bg-transparent text-white/40">o</span>
                </div>
              </div>

              <div className="text-center text-sm text-white/60">
                No tienes cuenta?{" "}
                <Link href="/register" className="text-emerald-400 hover:text-emerald-300 font-medium transition-colors">
                  Registrate
                </Link>
              </div>
            </form>

            <div className="px-8 pb-6 text-center">
              <p className="text-xs text-white/30">
                Al iniciar sesion, aceptas nuestros terminos y condiciones
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default LoginForm;
