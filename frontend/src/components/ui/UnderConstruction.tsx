import React from "react";
import Link from "next/link";
import { Hammer, ArrowRight } from "lucide-react";
import type { RelatedModuleLink } from "@/lib/productModules";

interface UnderConstructionProps {
  title?: string;
  message?: string;
  module?: string;
  relatedLinks?: RelatedModuleLink[];
}

export function UnderConstruction({
  title = "Página em Construção",
  message = "Estamos trabalhando duro para trazer essa funcionalidade em breve!",
  module,
  relatedLinks,
}: UnderConstructionProps) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4 animate-in fade-in duration-500 max-w-lg">
      <div className="bg-brand-green/10 p-6 rounded-full mb-6">
        <Hammer className="w-16 h-16 text-brand-green" />
      </div>
      {module && (
        <p className="text-xs font-semibold uppercase tracking-wider text-brand-green mb-2">
          {module}
        </p>
      )}
      <h2 className="text-3xl font-bold text-slate-900 mb-3">{title}</h2>
      <p className="text-slate-500 text-lg">{message}</p>

      {relatedLinks && relatedLinks.length > 0 && (
        <div className="mt-8 w-full">
          <p className="text-sm font-medium text-slate-600 mb-3">
            Módulos já disponíveis:
          </p>
          <div className="flex flex-wrap justify-center gap-2">
            {relatedLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium bg-white border border-slate-200 text-slate-700 hover:border-brand-green hover:text-brand-dark-green transition-colors"
              >
                {link.label}
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default UnderConstruction;
