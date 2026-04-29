// Root layout with AuthProvider.
import type { Metadata } from "next";
import { AuthProvider } from "@/contexts/AuthContext";
import "./globals.css";

export const metadata: Metadata = {
  title: "PRANELY - Gestión de Residuos Industriales",
  description: "Sistema SaaS B2B para gestión, trazabilidad y cumplimiento normativo de residuos industriales",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es">
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
