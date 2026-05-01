// Billing settings page - Glassmorphism billing management
"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { billingApi, type BillingPlan, type SubscriptionDetail, type UsageInfo } from "@/lib/billing-api";

// Plan pricing (supuestos - definidos por sistema)
const PLAN_PRICES: Record<string, string> = {
  free: "Gratuito",
  pro: "$299 USD/mes",
  enterprise: "$999 USD/mes",
};

const PLAN_LIMITS: Record<string, number> = {
  free: 100,
  pro: 2500,
  enterprise: 0, // unlimited
};

function BillingContent() {
  const router = useRouter();
  const { user, organization, token, permissions, role } = useAuth();
  const [subscription, setSubscription] = useState<SubscriptionDetail | null>(null);
  const [usage, setUsage] = useState<UsageInfo | null>(null);
  const [plans, setPlans] = useState<BillingPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isOwner = role === "owner";

  // Load billing data
  useEffect(() => {
    if (!token) return;

    const loadBillingData = async () => {
      try {
        setLoading(true);
        
        // Load all data in parallel
        const [subData, usageData, plansData] = await Promise.allSettled([
          billingApi.getSubscription(token),
          billingApi.getUsage(token),
          billingApi.listPlans(),
        ]);

        if (subData.status === "fulfilled") {
          setSubscription(subData.value);
        }
        if (usageData.status === "fulfilled") {
          setUsage(usageData.value);
        }
        if (plansData.status === "fulfilled") {
          setPlans(plansData.value.plans);
        }
      } catch (err) {
        console.error("Failed to load billing data:", err);
        setError("Error al cargar datos de facturación");
      } finally {
        setLoading(false);
      }
    };

    loadBillingData();
  }, [token]);

  // Handle checkout
  const handleCheckout = async (planCode: string) => {
    if (!isOwner) {
      setError("Solo el Owner puede cambiar el plan");
      return;
    }

    try {
      setCheckoutLoading(true);
      setError(null);

      const successUrl = `${window.location.origin}/billing?success=true&plan=${planCode}`;
      const cancelUrl = `${window.location.origin}/billing?canceled=true`;

      const checkout = await billingApi.createCheckout(token, planCode, successUrl, cancelUrl);
      
      // Redirect to Stripe checkout
      window.location.href = checkout.checkout_url;
    } catch (err) {
      console.error("Checkout failed:", err);
      setError("Error al crear sesión de pago. Por favor intenta de nuevo.");
      setCheckoutLoading(false);
    }
  };

  // Usage percentage
  const usagePercent = usage && usage.docs_limit > 0
    ? Math.min((usage.docs_used / usage.docs_limit) * 100, 100)
    : usage?.docs_limit === 0 ? 100 : 0;

  const usageColor = usagePercent >= 90 ? "rose" : usagePercent >= 75 ? "amber" : "emerald";

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Animated Background */}
      <div className="fixed inset-0 -z-10">
        <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900" />
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-emerald-500/20 rounded-full blur-3xl animate-pulse" />
        <div className="absolute top-1/3 right-1/4 w-80 h-80 bg-violet-500/15 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }} />
        <div className="absolute bottom-1/4 left-1/3 w-72 h-72 bg-blue-500/15 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '2s' }} />
      </div>

      {/* Header */}
      <header className="sticky top-0 z-50 backdrop-blur-xl bg-white/5 border-b border-white/10">
        <div className="max-w-[1920px] mx-auto px-6 py-4 flex justify-between items-center">
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.push("/dashboard")}
              className="p-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 backdrop-blur-md transition-colors"
            >
              <svg className="w-5 h-5 text-white/60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
            </button>
            
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-emerald-400 via-teal-500 to-emerald-600 flex items-center justify-center shadow-lg shadow-emerald-500/30">
              <span className="text-white font-black text-xl">P</span>
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight">PRANELY</h1>
              <p className="text-xs text-white/40">Facturación y Planes</p>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="px-4 py-2 rounded-2xl bg-white/10 backdrop-blur-md border border-white/10">
              <span className="text-sm font-medium text-white/80">{organization?.name || 'Org'}</span>
            </div>
            
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center text-white font-bold">
              {user?.email?.[0]?.toUpperCase() || 'U'}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-[1920px] mx-auto px-6 py-8">
        {/* Error Alert */}
        {error && (
          <div className="mb-6 p-4 rounded-2xl bg-rose-500/20 border border-rose-500/30 backdrop-blur-md">
            <div className="flex items-center gap-3">
              <svg className="w-5 h-5 text-rose-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-rose-200">{error}</p>
              <button
                onClick={() => setError(null)}
                className="ml-auto p-1 hover:bg-white/10 rounded-lg"
              >
                <svg className="w-4 h-4 text-rose-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>
        )}

        {/* Current Plan & Usage */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          {/* Current Subscription Card */}
          <div className="lg:col-span-2 rounded-3xl bg-white/5 border border-white/10 backdrop-blur-xl p-6 shadow-2xl">
            <h2 className="text-lg font-semibold text-white/70 mb-6 flex items-center gap-3">
              <svg className="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
              Plan Actual
            </h2>

            {loading ? (
              <div className="animate-pulse space-y-4">
                <div className="h-8 w-32 bg-white/10 rounded-xl" />
                <div className="h-4 w-48 bg-white/10 rounded" />
              </div>
            ) : subscription ? (
              <div className="space-y-6">
                {/* Plan Name & Status */}
                <div className="flex items-center gap-4">
                  <div className={`px-4 py-2 rounded-2xl text-lg font-bold backdrop-blur-md border ${
                    subscription.plan_code === "enterprise" ? "bg-violet-500/30 border-violet-500/40 text-violet-300" :
                    subscription.plan_code === "pro" ? "bg-blue-500/30 border-blue-500/40 text-blue-300" :
                    "bg-emerald-500/30 border-emerald-500/40 text-emerald-300"
                  }`}>
                    {subscription.plan_name}
                  </div>
                  <div className={`px-3 py-1 rounded-xl text-xs font-medium ${
                    subscription.status === "active" ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" :
                    subscription.status === "past_due" ? "bg-amber-500/20 text-amber-400 border border-amber-500/30" :
                    "bg-white/10 text-white/60 border border-white/20"
                  }`}>
                    {subscription.status.toUpperCase()}
                  </div>
                </div>

                {/* Period Info */}
                {subscription.current_period_start && (
                  <p className="text-sm text-white/50">
                    Periodo: {new Date(subscription.current_period_start).toLocaleDateString("es-MX")} - 
                    {subscription.current_period_end ? new Date(subscription.current_period_end).toLocaleDateString("es-MX") : "N/A"}
                  </p>
                )}

                {/* Usage Progress Bar */}
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-white/60">Uso del periodo</span>
                    <span className="text-white/80 font-medium">
                      {usage?.docs_used || 0} / {usage?.docs_limit || subscription.doc_limit || 0} docs
                    </span>
                  </div>
                  <div className="h-3 rounded-full bg-white/10 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        usageColor === "rose" ? "bg-gradient-to-r from-rose-500 to-red-500" :
                        usageColor === "amber" ? "bg-gradient-to-r from-amber-500 to-orange-500" :
                        "bg-gradient-to-r from-emerald-500 to-teal-500"
                      }`}
                      style={{ width: `${usagePercent}%` }}
                    />
                  </div>
                  {usagePercent >= 75 && (
                    <p className="text-xs text-amber-400">
                      ⚠️ {subscription.plan_code !== "enterprise" ? "Considera hacer upgrade" : ""}
                    </p>
                  )}
                </div>
              </div>
            ) : (
              <div className="text-center py-8">
                <p className="text-white/40">No hay suscripción activa</p>
              </div>
            )}
          </div>

          {/* Quick Stats */}
          <div className="rounded-3xl bg-gradient-to-br from-violet-500/20 to-purple-500/10 backdrop-blur-xl border border-violet-500/30 p-6 shadow-2xl">
            <h3 className="text-sm font-semibold text-white/50 uppercase tracking-wider mb-4">
              Resumen de Uso
            </h3>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-white/60 text-sm">Docs usados</span>
                <span className="text-white font-bold">{usage?.docs_used || 0}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-white/60 text-sm">Límite actual</span>
                <span className="text-white font-bold">
                  {usage?.docs_limit === 0 ? "∞" : usage?.docs_limit || subscription?.doc_limit || 0}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-white/60 text-sm">Ciclo</span>
                <span className="text-white/80 text-sm">{usage?.month_year || "N/A"}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-white/60 text-sm">Estado</span>
                <span className={usage?.is_locked ? "text-rose-400" : "text-emerald-400"}>
                  {usage?.is_locked ? "Bloqueado" : "Activo"}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Plans Comparison */}
        <div className="rounded-3xl bg-white/5 border border-white/10 backdrop-blur-xl p-6 shadow-2xl">
          <h2 className="text-lg font-semibold text-white/70 mb-6 flex items-center gap-3">
            <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
            Planes Disponibles
          </h2>

          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 animate-pulse">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-64 bg-white/10 rounded-2xl" />
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {plans.map((plan) => {
                const isCurrentPlan = subscription?.plan_code === plan.code;
                const isUpgrade = PLAN_LIMITS[plan.code] > (PLAN_LIMITS[subscription?.plan_code || "free"] || 0);

                return (
                  <div
                    key={plan.id}
                    className={`relative rounded-2xl p-6 backdrop-blur-md border transition-all duration-300 ${
                      isCurrentPlan
                        ? "bg-emerald-500/20 border-emerald-500/40"
                        : "bg-white/5 border-white/10 hover:border-white/20 hover:bg-white/10"
                    }`}
                  >
                    {/* Current Plan Badge */}
                    {isCurrentPlan && (
                      <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full bg-emerald-500 text-xs font-bold text-white">
                        Plan Actual
                      </div>
                    )}

                    {/* Plan Header */}
                    <div className="text-center mb-6">
                      <h3 className={`text-xl font-bold mb-2 ${
                        plan.code === "enterprise" ? "text-violet-300" :
                        plan.code === "pro" ? "text-blue-300" :
                        "text-emerald-300"
                      }`}>
                        {plan.name}
                      </h3>
                      <div className="text-3xl font-bold text-white mb-1">
                        {PLAN_PRICES[plan.code]}
                      </div>
                      <p className="text-sm text-white/50">
                        {plan.doc_limit === 0 ? "Documentos ilimitados" : `${plan.doc_limit} docs/mes`}
                      </p>
                    </div>

                    {/* Features */}
                    <ul className="space-y-3 mb-6">
                      {plan.features && Object.entries(plan.features).map(([key, enabled]) => (
                        <li key={key} className="flex items-center gap-2 text-sm">
                          {enabled ? (
                            <svg className="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                            </svg>
                          ) : (
                            <svg className="w-4 h-4 text-white/20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                          )}
                          <span className={enabled ? "text-white/80" : "text-white/30"}>
                            {key.charAt(0).toUpperCase() + key.slice(1)}
                          </span>
                        </li>
                      ))}
                    </ul>

                    {/* CTA Button */}
                    {isCurrentPlan ? (
                      <button
                        disabled
                        className="w-full py-3 rounded-xl bg-white/10 text-white/40 font-medium cursor-not-allowed"
                      >
                        Plan Actual
                      </button>
                    ) : isOwner ? (
                      <button
                        onClick={() => handleCheckout(plan.code)}
                        disabled={checkoutLoading}
                        className={`w-full py-3 rounded-xl font-medium transition-all ${
                          isUpgrade
                            ? "bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-white shadow-lg shadow-emerald-500/30"
                            : "bg-white/10 hover:bg-white/20 text-white/80"
                        } ${checkoutLoading ? "opacity-50 cursor-wait" : ""}`}
                      >
                        {checkoutLoading ? "Cargando..." : isUpgrade ? "Hacer Upgrade" : "Cambiar Plan"}
                      </button>
                    ) : (
                      <div className="w-full py-3 rounded-xl bg-white/5 text-center text-white/40 text-sm">
                        Solo el Owner puede cambiar el plan
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Stripe Notice */}
        <div className="mt-6 p-4 rounded-2xl bg-blue-500/10 border border-blue-500/20 backdrop-blur-md">
          <div className="flex items-start gap-3">
            <svg className="w-5 h-5 text-blue-400 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="text-sm text-blue-200">
              <p className="font-medium mb-1">Pagos procesagos por Stripe</p>
              <p className="text-white/60">
                Tu información de pago es procesada de forma segura por Stripe. 
                PRANELY no almacena datos de tarjetas de crédito.
              </p>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-white/5 py-6 mt-8">
        <div className="max-w-[1920px] mx-auto px-6 flex justify-between items-center text-sm text-white/30">
          <span>© 2024 PRANELY. Sistema Documental Maestro.</span>
          <div className="flex items-center gap-4">
            <span>NOM-052-SEMARNAT-2005</span>
            <span>•</span>
            <span>México</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default function BillingPage() {
  return (
    <ProtectedRoute fallbackPath="/login">
      <BillingContent />
    </ProtectedRoute>
  );
}