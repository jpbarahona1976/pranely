"""Dashboard page (protected)."""
"use client";

import { useAuth } from "@/contexts/AuthContext";
import { ProtectedRoute } from "@/components/ProtectedRoute";

function DashboardContent() {
  const { user, organization, logout } = useAuth();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">PRANELY</h1>
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-600">
              {user?.email}
              {organization && ` · ${organization.name}`}
            </span>
            <button
              onClick={logout}
              className="text-sm text-red-600 hover:text-red-800"
            >
              Cerrar sesión
            </button>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <h2 className="text-xl font-semibold text-gray-900 mb-6">
          Bienvenido{user?.full_name ? `, ${user.full_name}` : ""}
        </h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Quick stats placeholder */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Resumen</h3>
            <div className="space-y-4">
              <div className="flex justify-between">
                <span className="text-gray-600">Documentos</span>
                <span className="font-semibold">0</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Pendientes</span>
                <span className="font-semibold">0</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Validados</span>
                <span className="font-semibold">0</span>
              </div>
            </div>
          </div>

          {/* Quick actions placeholder */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Acciones rápidas</h3>
            <div className="space-y-3">
              <button className="w-full text-left px-4 py-2 bg-blue-50 text-blue-700 rounded hover:bg-blue-100">
                + Subir documento
              </button>
              <button className="w-full text-left px-4 py-2 bg-gray-50 text-gray-700 rounded hover:bg-gray-100">
                Ver cola de revisión
              </button>
              <button className="w-full text-left px-4 py-2 bg-gray-50 text-gray-700 rounded hover:bg-gray-100">
                Exportar reportes
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <ProtectedRoute fallbackPath="/login">
      <DashboardContent />
    </ProtectedRoute>
  );
}