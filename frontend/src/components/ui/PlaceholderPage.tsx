import { notFound } from "next/navigation";
import { getPlaceholderByPath } from "@/lib/productModules";
import { UnderConstruction } from "@/components/ui/UnderConstruction";

interface PlaceholderPageProps {
  path: string;
}

export function PlaceholderPage({ path }: PlaceholderPageProps) {
  const config = getPlaceholderByPath(path);
  if (!config) {
    notFound();
  }

  return (
    <div className="w-full h-full flex items-center justify-center bg-slate-50">
      <UnderConstruction
        title={config.title}
        message={config.message}
        module={config.module}
        relatedLinks={config.relatedLinks}
      />
    </div>
  );
}
