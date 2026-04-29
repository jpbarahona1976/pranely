// Registration form component - Glassmorphism style
"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";

export function RegisterForm() {
  const { register } = useAuth();
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    confirmPassword: "",
    fullName: "",
    orgName: "",
  });
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");

    if (formData.password !== formData.confirmPassword) {
      setError("Las contraseñas no coinciden");
      return;
    }

    if (formData.password.length < 8) {
      setError("La contraseña debe tener al menos 8 caracteres");
      return;
    }

    setIsLoading(true);

    try {
      await register(
        formData.email,
        formData.password,
        formData.fullName,
        formData.orgName
      );
      window.location.href = "/dashboard";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al registrarse");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen relative overflow-hidden flex items-center justify-center py-12 px-4">
      {/* Background - Same as dashboard */}
      <div className="fixed inset-0 -z-10">
        <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900" />
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-emerald-500/20 rounded-full blur-3xl animate-pulse" />
        <div className="absolute top-1/3 right-1/4 w-80 h-80 bg-violet-500/15 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }} />
        <div className="absolute bottom-1/4 left-1/3 w-72 h-72 bg-blue-500/15 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '2s' }} />
      </div>

      {/* Glass Card Container */}
      <div className="w-full max-w-md">
        <div className="relative">
          {/* Glow effect behind card */}
          <div className="absolute -inset-1 bg-gradient-to-r from-emerald-500/20 to-teal-500/20 rounded-3xl blur-xl opacity-50" />
          
          {/* Glass Card */}
          <div className="relative rounded-3xl bg-white/5 backdrop-blur-xl border border-white/10 shadow-2xl overflow-hidden">
            {/* Header */}
            <div className="p-8 pb-0 text-center">
              {/* Logo */}
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-emerald-400 via-teal-500 to-emerald-600 shadow-lg shadow-emerald-500/30 mb-6">
                <span className="text-white font-black text-2xl">P</span>
              </div>
              
              <h1 className="text-2xl font-bold text-white tracking-tight mb-2">
                PRANELY
              </h1>
              <p className="text-white/60 text-sm mb-6">
                Crea tu cuenta gratuita
              </p>
            </div>

            {/* Form */}
            <form className="p-8 pt-4 space-y-4" onSubmit={handleSubmit}>
              {/* Error Alert */}
              {error && (
                <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 flex items-start gap-3">
                  <svg className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <p className="text-sm text-rose-300">{error}</p>
                </div>
              )}

              {/* Email Field */}
              <div className="space-y-2">
                <label htmlFor="email" className="block text-sm font-medium text-white/70">
                  Correo electrónico <span className="text-rose-400">*</span>
                </label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="correo@ejemplo.com"
                  className="w-full px-4 py-3 rounded-xl 
                             bg-white/5 border border-white/10 
                             text-white placeholder-white/30
                             focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/30
                             transition-all duration-200"
                />
              </div>

              {/* Full Name */}
              <div className="space-y-2">
                <label htmlFor="fullName" className="block text-sm font-medium text-white/70">
                  Nombre completo
                </label>
                <input
                  id="fullName"
                  name="fullName"
                  type="text"
                  value={formData.fullName}
                  onChange={handleChange}
                  placeholder="Tu nombre"
                  className="w-full px-4 py-3 rounded-xl 
                             bg-white/5 border border-white/10 
                             text-white placeholder-white/30
                             focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/30
                             transition-all duration-200"
                />
              </div>

              {/* Organization Name */}
              <div className="space-y-2">
                <label htmlFor="orgName" className="block text-sm font-medium text-white/70">
                  Nombre de la empresa <span className="text-rose-400">*</span>
                </label>
                <input
                  id="orgName"
                  name="orgName"
                  type="text"
                  required
                  value={formData.orgName}
                  onChange={handleChange}
                  placeholder="Nombre de tu organización"
                  className="w-full px-4 py-3 rounded-xl 
                             bg-white/5 border border-white/10 
                             text-white placeholder-white/30
                             focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/30
                             transition-all duration-200"
                />
              </div>

              {/* Password Field */}
              <div className="space-y-2">
                <label htmlFor="password" className="block text-sm font-medium text-white/70">
                  Contraseña <span className="text-rose-400">*</span>
                </label>
                <input
                  id="password"
                  name="password"
                  type="password"
                  required
                  value={formData.password}
                  onChange={handleChange}
                  placeholder="Mínimo 8 caracteres"
                  className="w-full px-4 py-3 rounded-xl 
                             bg-white/5 border border-white/10 
                             text-white placeholder-white/30
                             focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/30
                             transition-all duration-200"
                />
              </div>

              {/* Confirm Password */}
              <div className="space-y-2">
                <label htmlFor="confirmPassword" className="block text-sm font-medium text-white/70">
                  Confirmar contraseña <span className="text-rose-400">*</span>
                </label>
                <input
                  id="confirmPassword"
                  name="confirmPassword"
                  type="password"
                  required
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  placeholder="Repite la contraseña"
                  className="w-full px-4 py-3 rounded-xl 
                             bg-white/5 border border-white/10 
                             text-white placeholder-white/30
                             focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/30
                             transition-all duration-200"
                />
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-3.5 px-4 rounded-xl
                           bg-gradient-to-r from-emerald-500 to-teal-500
                           text-white font-semibold text-sm
                           shadow-lg shadow-emerald-500/30
                           hover:shadow-emerald-500/50 hover:from-emerald-400 hover:to-teal-400
                           focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:ring-offset-2 focus:ring-offset-slate-900
                           disabled:opacity-50 disabled:cursor-not-allowed
                           transition-all duration-200
                           flex items-center justify-center gap-2"
              >
                {isLoading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>Creando cuenta...</span>
                  </>
                ) : (
                  <span>Crear cuenta</span>
                )}
              </button>

              {/* Divider */}
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-white/10" />
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="px-3 bg-transparent text-white/40">o</span>
                </div>
              </div>

              {/* Login Link */}
              <div className="text-center text-sm text-white/60">
                ¿Ya tienes cuenta?{" "}
                <Link 
                  href="/login" 
                  className="text-emerald-400 hover:text-emerald-300 font-medium transition-colors"
                >
                  Inicia sesión
                </Link>
              </div>
            </form>

            {/* Footer */}
            <div className="px-8 pb-6 text-center">
              <p className="text-xs text-white/30">
                Al registrarte, aceptas nuestros términos y condiciones
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default RegisterForm;
