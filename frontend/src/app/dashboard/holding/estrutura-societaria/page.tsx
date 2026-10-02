"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";
import {
  GitBranch,
  AlertCircle,
  ExternalLink,
  Info,
} from "lucide-react";
import { apoioService } from "@/services/apoio";
import { holdingService, OwnershipTreeNode } from "@/services/holding";

function formatPct(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "—";
  return `${value.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`;
}

function shortName(node: { nome_fantasia?: string; razao_social?: string }) {
  return node.nome_fantasia || node.razao_social || "Empresa";
}

interface SocioHolding {
  id: number;
  name: string;
  percentage: number;
  natureza: "PJ" | "PF";
  fromApoio?: boolean;
}

/**
 * Fallback visual se o cadastro de sócios da Moura Leite estiver vazio.
 * Só desenho; não entra no fator de consolidação.
 */
const SOCIOS_FALLBACK_MLDU: SocioHolding[] = [
  { id: -1, name: "SOMA", percentage: 29.49, natureza: "PJ" },
  { id: -2, name: "OCA", percentage: 29.49, natureza: "PJ" },
  { id: -3, name: "PR&F", percentage: 29.49, natureza: "PJ" },
  { id: -4, name: "PAULO", percentage: 2.89, natureza: "PF" },
  { id: -5, name: "FABIO", percentage: 2.89, natureza: "PF" },
  { id: -6, name: "FELIPE", percentage: 2.89, natureza: "PF" },
  { id: -7, name: "ANDRÉ", percentage: 2.89, natureza: "PF" },
];

function normalizeName(value?: string | null) {
  return (value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9&]/g, "");
}

function findMouraLeiteCompany(emps: any[]) {
  const bySienge = emps.find((e) => String(e.id) === "1");
  if (bySienge) return bySienge;
  return emps.find((e) => {
    const n = normalizeName(`${e.nomeFantasia || ""} ${e.razaoSocial || ""}`);
    return n.includes("mouraleite") || n === "mldu";
  });
}

function inferNatureza(s: {
  natureza?: string;
  tipo?: string;
  partner_company_id?: number | null;
  partner_user_id?: number | null;
  partner_name?: string;
}): "PJ" | "PF" {
  if (s.natureza === "PJ" || s.natureza === "PF") return s.natureza;
  if (s.partner_company_id) return "PJ";
  if (s.partner_user_id || (s.tipo || "").toUpperCase().includes("PF")) return "PF";
  return "PF";
}

/** Nome curto para o organograma (PJ mantém fantasia; PF usa o primeiro nome). */
function shortSocioLabel(fullName: string, natureza: "PJ" | "PF") {
  const cleaned = fullName.trim();
  if (!cleaned) return "Sócio";
  if (natureza === "PJ") return cleaned;
  const first = cleaned.split(/\s+/).find(Boolean) || cleaned;
  return first.toUpperCase();
}

function mapSociosFromApoio(raw: any[]): SocioHolding[] {
  const mapped = raw
    .map((s, idx) => {
      const natureza = inferNatureza(s);
      const fullName = String(s.partner_name || s.tipo || "Sócio").trim();
      return {
        id: s.id ?? idx,
        name: shortSocioLabel(fullName, natureza),
        percentage: Number(s.percentage) || 0,
        natureza,
        fromApoio: true,
      };
    })
    .filter((s) => s.name);
  // PJ à esquerda, depois PF; empate por % decrescente
  return mapped.sort((a, b) => {
    if (a.natureza !== b.natureza) return a.natureza === "PJ" ? -1 : 1;
    return b.percentage - a.percentage;
  });
}

function sociosParaExibir(mapped: SocioHolding[]): SocioHolding[] {
  return mapped.length ? mapped : SOCIOS_FALLBACK_MLDU;
}

function isShareholderCompany(
  node: { nome_fantasia?: string; razao_social?: string },
  socios: SocioHolding[]
) {
  const keys = new Set(
    [...SOCIOS_FALLBACK_MLDU, ...socios]
      .filter((s) => s.natureza === "PJ")
      .map((s) => normalizeName(s.name))
  );
  return keys.has(normalizeName(node.nome_fantasia)) || keys.has(normalizeName(node.razao_social));
}

function OrgCard({
  node,
  isRoot,
}: {
  node: OwnershipTreeNode;
  isRoot?: boolean;
}) {
  return (
    <div
      className={`relative w-[168px] rounded-lg px-3 py-2.5 text-center shadow-sm ${
        isRoot
          ? "bg-ml-green text-white border border-emerald-800"
          : "bg-white text-slate-800 border border-slate-200"
      }`}
    >
      <p className={`text-[11px] font-bold leading-tight uppercase tracking-wide ${isRoot ? "text-white" : "text-slate-800"}`}>
        {shortName(node)}
      </p>
      <p className={`text-[10px] mt-0.5 ${isRoot ? "text-emerald-100" : "text-slate-400"}`}>
        {isRoot ? "Holding" : `id ${node.id_sienge}`}
      </p>
      {!isRoot && (
        <p className="text-[10px] text-slate-500 mt-1" title={node.calculo_tooltip}>
          Participação MLDU: <span className="font-semibold text-ml-green">{formatPct(node.participacao_efetiva)}</span>
        </p>
      )}
      <div className="flex items-center justify-center mt-2">
        <Link
          href={`/dashboard/apoio/empresas?socios=${node.company_id}`}
          className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium ${
            isRoot ? "text-white/90 hover:bg-white/15" : "text-slate-500 hover:bg-emerald-50 hover:text-ml-green"
          }`}
          title="Abrir sócios desta empresa no Apoio"
        >
          <ExternalLink className="w-3 h-3" />
          Sócios
        </Link>
      </div>
    </div>
  );
}

function OrgNote({
  node,
  onSave,
}: {
  node: OwnershipTreeNode;
  onSave: (linkId: number, notes: string) => Promise<void>;
}) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(node.notes || "");
  const [saving, setSaving] = useState(false);
  if (!node.link_id) return null;

  const salvar = async () => {
    setSaving(true);
    try {
      await onSave(node.link_id!, text.trim());
      setEditing(false);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mt-2 w-[190px]">
      {editing ? (
        <div className="space-y-1">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={5}
            className="w-full rounded-md border border-slate-300 bg-white px-2 py-1 text-[10px] leading-snug text-slate-700"
          />
          <div className="flex justify-end gap-1">
            <button
              type="button"
              className="px-1.5 py-0.5 text-[10px] text-slate-500"
              onClick={() => {
                setText(node.notes || "");
                setEditing(false);
              }}
            >
              Cancelar
            </button>
            <button
              type="button"
              disabled={saving}
              className="px-1.5 py-0.5 text-[10px] font-medium text-ml-green"
              onClick={salvar}
            >
              {saving ? "Salvando..." : "Salvar"}
            </button>
          </div>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => {
            setText(node.notes || "");
            setEditing(true);
          }}
          className="w-full rounded-md border border-dashed border-slate-300 bg-white/80 px-2 py-1.5 text-left text-[10px] leading-snug text-slate-600 hover:border-ml-green"
          title="Editar nota"
        >
          {node.notes?.trim() ? node.notes : "Adicionar nota"}
        </button>
      )}
    </div>
  );
}

function HoldingShareholders({ socios }: { socios: SocioHolding[] }) {
  if (!socios.length) return null;
  return (
    <div className="flex flex-col items-center">
      <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-3">Sócios da Moura Leite</p>
      <div className="flex items-end justify-center">
        {socios.map((socio, idx) => (
          <div key={socio.id} className="relative flex flex-col items-center px-1.5">
            <div
              className={`w-[112px] rounded-md border px-2 py-2 text-center shadow-sm ${
                socio.natureza === "PF"
                  ? "bg-brand-orange/10 border-brand-orange-light"
                  : "bg-white border-slate-300"
              }`}
            >
              <p className="text-[11px] font-bold uppercase tracking-wide text-slate-800 leading-tight">{socio.name}</p>
              <p className={`text-[9px] mt-0.5 tracking-wider ${socio.natureza === "PF" ? "text-brand-orange" : "text-slate-400"}`}>
                {socio.natureza}
              </p>
            </div>
            <span className="text-[11px] font-bold text-ml-green leading-none my-1.5 bg-[#F3F6F3] px-1">
              {formatPct(socio.percentage)}
            </span>
            <div className="w-px h-4 bg-slate-300" />
            {socios.length > 1 ? (
              <div
                className={`absolute bottom-0 h-px bg-slate-300 ${
                  idx === 0 ? "left-1/2 right-0" : idx === socios.length - 1 ? "left-0 right-1/2" : "left-0 right-0"
                }`}
              />
            ) : null}
          </div>
        ))}
      </div>
      <div className="w-px h-5 bg-slate-300" />
    </div>
  );
}

function OrgChildren({
  nodes,
  onSaveNote,
}: {
  nodes: OwnershipTreeNode[];
  onSaveNote: (linkId: number, notes: string) => Promise<void>;
}) {
  if (!nodes.length) return null;
  return (
    <div className="flex flex-col items-center">
      <div className="w-px h-5 bg-slate-300" />
      <div className="flex items-start justify-center">
        {nodes.map((child, idx) => (
          <div key={child.link_id ?? child.company_id} className="relative flex flex-col items-center px-3">
            {nodes.length > 1 ? (
              <div
                className={`absolute top-0 h-px bg-slate-300 ${
                  idx === 0 ? "left-1/2 right-0" : idx === nodes.length - 1 ? "left-0 right-1/2" : "left-0 right-0"
                }`}
              />
            ) : null}
            <div className="w-px h-4 bg-slate-300" />
            <span className="text-[11px] font-bold text-ml-green leading-none mb-1.5 bg-[#F3F6F3] px-1">
              {formatPct(child.percentage)}
            </span>
            <OrgCard node={child} />
            <OrgNote node={child} onSave={onSaveNote} />
            <OrgChildren nodes={child.children || []} onSaveNote={onSaveNote} />
          </div>
        ))}
      </div>
    </div>
  );
}

export default function EstruturaSocietariaPage() {
  const [tree, setTree] = useState<OwnershipTreeNode | null>(null);
  const [semVinculo, setSemVinculo] = useState<OwnershipTreeNode[]>([]);
  const [divergencias, setDivergencias] = useState<{ nome: string; pai: string; apoio_pct: number; consolidacao_pct: number }[]>([]);
  const [sociosHolding, setSociosHolding] = useState<SocioHolding[]>([]);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError("");
    try {
      const [estrutura, emps] = await Promise.all([
        holdingService.getEstrutura(),
        apoioService.getEmpresas(),
      ]);
      setTree(estrutura.root);
      setSemVinculo(estrutura.empresas_sem_vinculo || []);
      setDivergencias(estrutura.divergencias || []);
      if (estrutura.message && !estrutura.root) {
        setError(estrutura.message);
      }
      const mldu = findMouraLeiteCompany(emps);
      if (mldu?.db_id) {
        const socios = await apoioService.getCompanyPartners(mldu.db_id);
        const mapped = mapSociosFromApoio(Array.isArray(socios) ? socios : []);
        setSociosHolding(sociosParaExibir(mapped));
      } else {
        setSociosHolding(SOCIOS_FALLBACK_MLDU);
      }
    } catch (e: any) {
      setError(e.response?.data?.detail || "Erro ao carregar estrutura.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const salvarNota = async (linkId: number, notes: string) => {
    setError("");
    try {
      await holdingService.updateLink(linkId, { notes });
      const estrutura = await holdingService.getEstrutura();
      setTree(estrutura.root);
    } catch (e: any) {
      setError(e.response?.data?.detail || "Erro ao salvar a nota.");
      throw e;
    }
  };

  const temFilhos = Boolean(tree?.children?.length);

  if (isLoading) {
    return <AppLoadingState />;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-10 h-10 rounded-lg bg-emerald-50 border border-emerald-100 flex items-center justify-center text-emerald-600 shrink-0">
            <GitBranch size={20} />
          </div>
          <div className="min-w-0">
            <h1 className="text-xl font-bold text-slate-800">Organograma</h1>
            <p className="text-sm text-slate-500 mt-0.5">
              Nomes e percentuais vêm de{" "}
              <Link href="/dashboard/apoio/empresas" className="text-ml-green font-medium hover:underline inline-flex items-center gap-0.5">
                Apoio → Empresas <ExternalLink className="w-3 h-3" />
              </Link>
              . A participação MLDU é o quanto a holding fica no fim da cadeia.
            </p>
          </div>
        </div>
      </div>

      {error ? (
        <div className="flex items-start gap-2 p-3 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-sm">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          {error}
        </div>
      ) : null}

      <div className="grid md:grid-cols-3 gap-3">
        <div className="bg-white rounded-xl border border-slate-200 px-4 py-3">
          <p className="text-[10px] font-bold uppercase tracking-wider text-ml-green">1 · Ler o quadro</p>
          <p className="text-sm text-slate-600 mt-1">
            Acima da caixa verde estão os sócios da holding. Abaixo, as empresas. O número na linha é a participação direta cadastrada no Apoio.
          </p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 px-4 py-3">
          <p className="text-[10px] font-bold uppercase tracking-wider text-ml-green">2 · Alterar</p>
          <p className="text-sm text-slate-600 mt-1">
            Sócios abre o cadastro daquela empresa. O percentual, o nome e quem entra ou sai mudam lá.
          </p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 px-4 py-3">
          <p className="text-[10px] font-bold uppercase tracking-wider text-ml-green">3 · Participação</p>
          <p className="text-sm text-slate-600 mt-1">
            Participação MLDU é a conta da cadeia. Não se digita no cadastro.
          </p>
        </div>
      </div>

      {divergencias.length > 0 ? (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
          <p className="flex items-center gap-2 font-medium">
            <AlertCircle className="w-4 h-4 text-amber-600" />
            O Apoio e a consolidação estão diferentes. A consolidação não foi alterada.
          </p>
          <ul className="mt-2 text-xs space-y-0.5 list-disc pl-9">
            {divergencias.map((item) => (
              <li key={item.nome}>
                {item.nome} ({item.pai}): Apoio {formatPct(item.apoio_pct)} · consolidação {formatPct(item.consolidacao_pct)}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-5 py-3 border-b border-slate-100 flex items-start justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-slate-800">Árvore societária</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Sócios acima da caixa verde. % na linha = participação direta. “Participação MLDU” = o quanto a holding fica no fim da cadeia.
            </p>
          </div>
          <div className="hidden sm:flex items-center gap-2 text-[11px] text-slate-500">
            <span className="inline-flex items-center gap-1"><span className="inline-block w-3 h-3 rounded-sm bg-white border border-slate-300" /> Sócio PJ</span>
            <span className="inline-flex items-center gap-1"><span className="inline-block w-3 h-3 rounded-sm bg-brand-orange/10 border border-brand-orange-light" /> Sócio PF</span>
            <span className="inline-flex items-center gap-1"><span className="inline-block w-3 h-3 rounded-sm bg-ml-green" /> Holding</span>
            <span className="inline-flex items-center gap-1"><span className="inline-block w-3 h-3 rounded-sm bg-white border border-slate-300" /> Participada</span>
          </div>
        </div>

        <div className="overflow-x-auto bg-[#F3F6F3] px-6 py-10 min-h-[320px]">
          {tree ? (
            <div className="flex flex-col items-center min-w-max mx-auto">
              <HoldingShareholders socios={sociosHolding} />

              <OrgCard node={tree} isRoot />

              {temFilhos ? (
                <OrgChildren nodes={tree.children || []} onSaveNote={salvarNota} />
              ) : (
                <div className="mt-8 max-w-md text-center">
                  <div className="w-px h-8 bg-slate-300 mx-auto mb-3" />
                  <p className="text-sm font-medium text-slate-700">Nenhuma empresa ligada ainda</p>
                  <p className="text-xs text-slate-500 mt-1">
                    No Apoio, cadastre na empresa de baixo o sócio da empresa de cima, com o percentual direto.
                  </p>
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-center text-slate-500">
              Empresa raiz (Moura Leite, id Sienge 1) não encontrada. Sincronize empresas em Apoio.
            </p>
          )}
        </div>
      </div>

      {semVinculo.filter((e) => !isShareholderCompany(e, sociosHolding)).length > 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <div className="flex items-start gap-2 mb-3">
            <Info className="w-4 h-4 text-slate-400 mt-0.5 shrink-0" />
            <div>
              <h2 className="text-sm font-semibold text-slate-800">Cadastradas, ainda fora da árvore</h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Para entrar no quadro, cadastre nela o sócio da empresa de cima.
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            {semVinculo.filter((e) => !isShareholderCompany(e, sociosHolding)).map((e) => (
              <Link
                key={e.company_id}
                href={`/dashboard/apoio/empresas?socios=${e.company_id}`}
                className="text-xs px-2.5 py-1 rounded-full border border-slate-200 bg-slate-50 text-slate-600 hover:border-ml-green hover:text-ml-green hover:bg-emerald-50 transition-colors"
              >
                {e.nome_fantasia || e.razao_social}
              </Link>
            ))}
          </div>
        </div>
      ) : null}

    </div>
  );
}
