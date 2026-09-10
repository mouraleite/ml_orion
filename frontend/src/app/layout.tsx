import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/contexts/AuthContext";
import { UnsavedChangesProvider } from "@/contexts/UnsavedChangesContext";
import { Toaster } from "react-hot-toast";
import { ConfirmHost } from "@/components/ui/confirmDialog";

export const metadata: Metadata = {
  title: "ERP ML",
  description: "Plataforma Corporativa de Gestão",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className="h-full antialiased"
    >
      <body className="min-h-full flex flex-col">
        <AuthProvider>
          <UnsavedChangesProvider>
            {children}
            <ConfirmHost />
            <Toaster position="top-right" />
          </UnsavedChangesProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
