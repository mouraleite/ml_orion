"use client";
import { useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { AppLoadingScreen } from "@/components/shared/BudgetLoadingState";

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading } = useAuth();

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      window.location.href = "/login";
    }
  }, [isAuthenticated, loading]);

  if (loading) {
    return <AppLoadingScreen />;
  }

  if (!isAuthenticated) {
    return null; // Evita piscar conteúdo antes do redirecionamento
  }

  return <>{children}</>;
}
