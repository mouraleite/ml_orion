"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";
import {
  GitBranch,
  Plus,
  RefreshCw,
  Trash2,
  Pencil,
  AlertCircle,
  ExternalLink,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Info,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { confirmDialog } from "@/components/ui/confirmDialog";
import { apoioService } from "@/services/apoio";
import { holdingService, OwnershipTreeNode, OrganogramaValidacaoResponse } from "@/services/holding";

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

interface OrgActions {
  onEdit: (node: OwnershipTreeNode) => void;
  onDelete: (linkId: number) => void;
  onAddChild: (parentCompanyId: number) => void;
}

function OrgCard({
  node,
  isRoot,
  actions,
}: {
  node: OwnershipTreeNode;
  isRoot?: boolean;
  actions: OrgActions;
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
        {isRoot ? "MOURA LEITE" : shortName(node)}
      </p>
      <p className={`text-[10px] mt-0.5 ${isRoot ? "text-emerald-100" : "text-slate-400"}`}>
        {isRoot ? "Holding" : `id ${node.id_sienge}`}
      </p>
      {!isRoot && (
        <p className="text-[10px] text-slate-500 mt-1" title={node.calculo_tooltip}>
          Fatia MLDU: <span className="font-semibold text-ml-green">{formatPct(node.participacao_efetiva)}</span>
        </p>
      )}
      <div className="flex items-center justify-center gap-1 mt-2">
        {!isRoot && node.link_id ? (
          <>
            <button
              type="button"
              onClick={() => actions.onEdit(node)}
              className="p-1 rounded text-slate-500 hover:bg-emerald-50 hover:text-ml-green"
              title="Alterar participação"
            >
              <Pencil className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={() => actions.onDelete(node.link_id!)}
              className="p-1 rounded text-slate-400 hover:bg-red-50 hover:text-red-600"
              title="Remover da árvore"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </>
        ) : null}
        <button
          type="button"
          onClick={() => actions.onAddChild(node.company_id)}
          className={`p-1 rounded ${isRoot ? "text-white/90 hover:bg-white/15" : "text-slate-500 hover:bg-emerald-50 hover:text-ml-green"}`}
          title="Ligar uma empresa abaixo desta"
        >
          <Plus className="w-3.5 h-3.5" />
        </button>
      </div>
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

function OrgChildren({ nodes, actions }: { nodes: OwnershipTreeNode[]; actions: OrgActions }) {
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
            <OrgCard node={child} actions={actions} />
            <OrgChildren nodes={child.children || []} actions={actions} />
          </div>
        ))}
      </div>
    </div>
  );
}

export default function EstruturaSocietariaPage() {
  const [tree, setTree] = useState<OwnershipTreeNode | null>(null);
  const [semVinculo, setSemVinculo] = useState<OwnershipTreeNode[]>([]);
  const [empresas, setEmpresas] = useState<any[]>([]);
  const [sociosHolding, setSociosHolding] = useState<SocioHolding[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingLinkId, setEditingLinkId] = useState<number | null>(null);
  const [parentPreset, setParentPreset] = useState<number | "">("");
  const [form, setForm] = useState({
    parent_company_id: "",
    child_company_id: "",
    percentage: "",
    consolidates: true,
    notes: "",
    valid_from: "",
  });
  const [originalPercentage, setOriginalPercentage] = useState<number | null>(null);
  const [historico, setHistorico] = useState<{ percentage: number; valid_from: string | null; valid_until: string | null }[]>([]);
  const [validacao, setValidacao] = useState<OrganogramaValidacaoResponse | null>(null);
  const [showValidacao, setShowValidacao] = useState(false);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError("");
    try {
      const [estrutura, emps, val] = await Promise.all([
        holdingService.getEstrutura(),
        apoioService.getEmpresas(),
        holdingService.getValidacaoOrganograma(),
      ]);
      setTree(estrutura.root);
      setSemVinculo(estrutura.empresas_sem_vinculo || []);
      setEmpresas(emps);
      setValidacao(val);
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

  const openCreate = (parentCompanyId?: number, childCompanyId?: number) => {
    setEditingLinkId(null);
    setParentPreset(parentCompanyId ?? "");
    setForm({
      parent_company_id: parentCompanyId ? String(parentCompanyId) : "",
      child_company_id: childCompanyId ? String(childCompanyId) : "",
      percentage: "",
      consolidates: true,
      notes: "",
      valid_from: "",
    });
    setOriginalPercentage(null);
    setHistorico([]);
    setIsModalOpen(true);
  };

  const openEdit = (node: OwnershipTreeNode) => {
    if (!node.link_id) return;
    setEditingLinkId(node.link_id);
    setForm({
      parent_company_id: "",
      child_company_id: String(node.company_id),
      percentage: String(node.percentage ?? ""),
      consolidates: node.consolidates ?? true,
      notes: node.notes || "",
      valid_from: "",
    });
    setOriginalPercentage(node.percentage ?? null);
    setHistorico(node.historico || []);
    setIsModalOpen(true);
  };

  const handleSave = async () => {
    setError("");
    try {
      const pct = parseFloat(form.percentage.replace(",", "."));
      if (Number.isNaN(pct) || pct < 0 || pct > 100) {
        setError("Percentual deve estar entre 0 e 100.");
        return;
      }

      if (editingLinkId) {
        const pctMudou = originalPercentage == null || Math.abs(pct - originalPercentage) >= 0.0001;
        if (pctMudou && !form.valid_from) {
          setError("Informe o mês a partir do qual o novo % vale. Os meses anteriores ficam com o percentual antigo.");
          return;
        }
        await holdingService.updateLink(editingLinkId, {
          percentage: pct,
          consolidates: form.consolidates,
          notes: form.notes || undefined,
          valid_from: pctMudou ? form.valid_from : undefined,
        });
        setMessage("Participação atualizada. O passado permanece como estava.");
      } else {
        const parentId = parseInt(form.parent_company_id || String(parentPreset), 10);
        const childId = parseInt(form.child_company_id, 10);
        if (!parentId || !childId) {
          setError("Selecione a holding (ou empresa acima) e a empresa que será ligada.");
          return;
        }
        await holdingService.createLink({
          parent_company_id: parentId,
          child_company_id: childId,
          percentage: pct,
          consolidates: form.consolidates,
          notes: form.notes || undefined,
        });
        setMessage("Empresa ligada à árvore.");
      }
      setIsModalOpen(false);
      await load();
      setTimeout(() => setMessage(""), 4000);
    } catch (e: any) {
      setError(e.response?.data?.detail || "Erro ao salvar.");
    }
  };

  const handleDelete = async (linkId: number) => {
    if (!(await confirmDialog("Remover esta empresa da árvore da holding? O cadastro dela no Apoio permanece.", {
      title: "Remover da árvore",
      confirmLabel: "Remover",
      variant: "danger",
    }))) return;
    try {
      await holdingService.deleteLink(linkId);
      setMessage("Empresa removida da árvore.");
      await load();
      setTimeout(() => setMessage(""), 3000);
    } catch (e: any) {
      setError(e.response?.data?.detail || "Erro ao remover.");
    }
  };

  const handleSeed = async () => {
    if (!(await confirmDialog("Montar a árvore com o organograma oficial da Moura Leite? Só cria o que ainda não existe. Não apaga o que você já ligou.", {
      title: "Carregar organograma oficial",
      confirmLabel: "Carregar",
    }))) return;
    try {
      const result = await holdingService.seedReferencia();
      setMessage(
        result.created
          ? `Organograma carregado: ${result.created} empresa(s) ligada(s).`
          : "Nada novo para ligar — as empresas de referência já estão na árvore ou ainda não existem no Apoio."
      );
      await load();
      setTimeout(() => setMessage(""), 6000);
    } catch (e: any) {
      setError(e.response?.data?.detail || "Erro ao carregar o organograma.");
    }
  };

  const empresaOptions = empresas.map((e) => ({
    db_id: e.db_id,
    label: `${e.nomeFantasia || e.razaoSocial} (id ${e.id})`,
  }));

  const actions: OrgActions = {
    onEdit: openEdit,
    onDelete: handleDelete,
    onAddChild: (id) => openCreate(id),
  };

  const temFilhos = Boolean(tree?.children?.length);
  const divergencias = validacao?.empresas.filter((e) => e.status === "divergente") || [];

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
            <h1 className="text-xl font-bold text-slate-800">Organograma da holding</h1>
            <p className="text-sm text-slate-500 mt-0.5">
              Quem a Moura Leite controla, e com qual %. Sócios da própria holding ficam em{" "}
              <Link href="/dashboard/apoio/empresas" className="text-ml-green font-medium hover:underline inline-flex items-center gap-0.5">
                Apoio → Empresas <ExternalLink className="w-3 h-3" />
              </Link>
              .
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2 shrink-0">
          <Button variant="secondary" onClick={handleSeed} className="gap-2">
            <RefreshCw size={16} />
            Carregar organograma oficial
          </Button>
          <Button onClick={() => openCreate(tree?.company_id)} className="gap-2">
            <Plus size={16} />
            Ligar empresa
          </Button>
        </div>
      </div>

      {message ? <p className="text-sm text-emerald-700 font-medium -mt-2">{message}</p> : null}

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
            Acima da caixa verde estão os sócios da Moura Leite. Abaixo, as empresas da holding. O número na linha é a participação <strong>direta</strong>.
          </p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 px-4 py-3">
          <p className="text-[10px] font-bold uppercase tracking-wider text-ml-green">2 · Alterar um %</p>
          <p className="text-sm text-slate-600 mt-1">
            Clique no lápis da caixa. Informe o mês em que o novo % começa. Meses anteriores não mudam.
          </p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 px-4 py-3">
          <p className="text-[10px] font-bold uppercase tracking-wider text-ml-green">3 · Ligar ou tirar</p>
          <p className="text-sm text-slate-600 mt-1">
            <strong>+</strong> liga uma empresa embaixo. A lixeira só tira da árvore — o cadastro no Apoio continua.
          </p>
        </div>
      </div>

      {validacao && divergencias.length > 0 ? (
        <div className="rounded-xl border border-amber-200 bg-amber-50">
          <button
            type="button"
            onClick={() => setShowValidacao((v) => !v)}
            className="w-full flex items-center justify-between px-4 py-3 text-left text-sm text-amber-950"
          >
            <span className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-amber-600" />
              {temFilhos
                ? `${divergencias.length} empresa(s) com % diferente da referência oficial`
                : "A árvore ainda está vazia — por isso a conferência mostra 0%"}
            </span>
            {showValidacao ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
          {showValidacao ? (
            <ul className="px-4 pb-3 text-xs text-amber-900/90 space-y-0.5 list-disc pl-10">
              {divergencias.map((e) => (
                <li key={e.id_sienge}>
                  {e.nome || `id ${e.id_sienge}`}: referência {formatPct(e.expected_pct)} · atual {formatPct(e.actual_pct)}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : validacao?.ok ? (
        <div className="flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-2.5 text-sm text-emerald-900">
          <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          Organograma alinhado à referência oficial.
        </div>
      ) : null}

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-5 py-3 border-b border-slate-100 flex items-start justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-slate-800">Árvore societária</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Sócios acima da caixa verde. % na linha = participação direta. “Fatia MLDU” = o quanto a holding fica no fim da cadeia.
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

              <OrgCard node={tree} isRoot actions={actions} />

              {temFilhos ? (
                <OrgChildren nodes={tree.children || []} actions={actions} />
              ) : (
                <div className="mt-8 max-w-md text-center">
                  <div className="w-px h-8 bg-slate-300 mx-auto mb-3" />
                  <p className="text-sm font-medium text-slate-700">Nenhuma empresa ligada ainda</p>
                  <p className="text-xs text-slate-500 mt-1 mb-4">
                    Carregue o organograma oficial (Ellenco, MLES, Ypês…) ou ligue a primeira empresa à caixa verde.
                  </p>
                  <div className="flex flex-wrap justify-center gap-2">
                    <Button onClick={handleSeed} className="gap-2">
                      <RefreshCw size={14} />
                      Carregar organograma oficial
                    </Button>
                    <Button variant="secondary" onClick={() => openCreate(tree.company_id)} className="gap-2">
                      <Plus size={14} />
                      Ligar empresa
                    </Button>
                  </div>
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
                Existem no Sienge/Apoio, mas a holding ainda não tem um % nelas. Clique para ligar.
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            {semVinculo.filter((e) => !isShareholderCompany(e, sociosHolding)).map((e) => (
              <button
                key={e.company_id}
                type="button"
                onClick={() => openCreate(tree?.company_id, e.company_id)}
                className="text-xs px-2.5 py-1 rounded-full border border-slate-200 bg-slate-50 text-slate-600 hover:border-ml-green hover:text-ml-green hover:bg-emerald-50 transition-colors"
                title="Ligar esta empresa à holding"
              >
                {e.nome_fantasia || e.razao_social}
              </button>
            ))}
          </div>
        </div>
      ) : null}

      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingLinkId ? "Alterar participação" : "Ligar empresa à árvore"}
        size="md"
      >
        <div className="space-y-4">
          <p className="text-xs text-slate-500">
            {editingLinkId
              ? "Se o % mudar, o mês de início é obrigatório. O consolidado dos meses anteriores não se altera."
              : "Escolha quem fica acima, quem entra abaixo e o % direto neste vínculo."}
          </p>
          {!editingLinkId && (
            <>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Empresa acima (quem participa)</label>
                <select
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm"
                  value={form.parent_company_id || parentPreset}
                  onChange={(e) => setForm({ ...form, parent_company_id: e.target.value })}
                >
                  <option value="">Selecione…</option>
                  {empresaOptions.map((o) => (
                    <option key={o.db_id} value={o.db_id}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Empresa que entra na árvore</label>
                <select
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm"
                  value={form.child_company_id}
                  onChange={(e) => setForm({ ...form, child_company_id: e.target.value })}
                >
                  <option value="">Selecione…</option>
                  {empresaOptions.map((o) => (
                    <option key={o.db_id} value={o.db_id}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </div>
            </>
          )}
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Participação direta (%)</label>
            <Input
              value={form.percentage}
              onChange={(e) => setForm({ ...form, percentage: e.target.value })}
              placeholder="Ex.: 50 ou 55,5"
            />
          </div>
          {editingLinkId ? (
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Novo % a partir de (mês)</label>
              <input
                type="month"
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm"
                value={form.valid_from}
                onChange={(e) => setForm({ ...form, valid_from: e.target.value })}
              />
              <p className="text-xs text-slate-500 mt-1">
                Obrigatório só se o percentual mudar. Meses anteriores permanecem com o % antigo.
              </p>
            </div>
          ) : null}
          {historico.length > 0 ? (
            <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
              <p className="text-xs font-semibold text-slate-600 mb-1">Histórico deste vínculo</p>
              <ul className="text-xs text-slate-600 space-y-0.5">
                {historico.map((faixa, idx) => (
                  <li key={`${faixa.valid_from}-${idx}`}>
                    {formatPct(faixa.percentage)}
                    {" · "}
                    {faixa.valid_from || "início"}
                    {" → "}
                    {faixa.valid_until || "atual"}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={form.consolidates}
              onChange={(e) => setForm({ ...form, consolidates: e.target.checked })}
            />
            Entra na consolidação MLDU
          </label>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Observações</label>
            <Input
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              placeholder="Opcional"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setIsModalOpen(false)}>
              Cancelar
            </Button>
            <Button onClick={handleSave}>Salvar</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
