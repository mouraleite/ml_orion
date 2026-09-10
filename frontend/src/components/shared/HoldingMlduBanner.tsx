"use client";

import { AlertCircle } from "lucide-react";
import Link from "next/link";

interface HoldingMlduBannerProps {
  avisos?: string[];
}

export function HoldingMlduBanner({ avisos }: HoldingMlduBannerProps) {
  return (
    <div className="rounded-lg border border-orange-200 bg-orange-50 px-4 py-3 text-sm text-orange-950">
      <div className="flex items-start gap-2">
        <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-[#F5883A]" />
        <div>
          <p>
            <strong>Consolidação MLDU ativa</strong> — valores ponderados pelo % efetivo de participação da
            holding Moura Leite. Modo <strong>somente leitura</strong>; nada é gravado no banco.
          </p>
          <p className="text-xs text-orange-800/80 mt-1">
            Percentuais em{" "}
            <Link href="/dashboard/holding/estrutura-societaria" className="underline font-medium">
              Consolidação → Estrutura societária MLDU
            </Link>
            .
          </p>
          {avisos && avisos.length > 0 && (
            <ul className="mt-2 text-xs list-disc pl-4 space-y-0.5 text-orange-900/90">
              {avisos.slice(0, 5).map((msg) => (
                <li key={msg}>{msg}</li>
              ))}
              {avisos.length > 5 && <li>+{avisos.length - 5} aviso(s)</li>}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
