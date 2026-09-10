const fs = require('fs');
const FILE = 'c:/Users/Usuario/Desktop/Em Desenvolvimento/Meus Projetos/ERP ML/frontend/src/app/dashboard/orcamento/realizado/page.tsx';
let c = fs.readFileSync(FILE, 'utf8');

const tabCompOld = `function TabComparativo({ ano, deptId }: { ano: number; deptId: number }) {
  const [versoesDespesas, setVersoesDespesas] = useState<any[]>([]);
  const [versoesVendas, setVersoesVendas] = useState<any[]>([]);
  const [tipo, setTipo] = useState("DESPESAS");
  const [idA, setIdA] = useState<number | "">("");
  const [idB, setIdB] = useState<number | "">("");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    orcamentoService.listarVersoes(ano, "DESPESAS", deptId).then(setVersoesDespesas).catch(() => { });
    orcamentoService.listarVersoes(ano, "VENDAS", deptId).then(setVersoesVendas).catch(() => { });
  }, [ano, deptId]);

  const versoes = tipo === "DESPESAS" ? versoesDespesas : versoesVendas;
  const getProdNome = (id: number) => result?.produtos_map?.[id] || id;
  const getPlanoNome = (id: number) => result?.planos_map?.[id] || id;

  const comparar = async () => {
    if (!idA || !idB) return;
    setLoading(true);
    try {
      const res = await (orcamentoService as any).getComparativo(Number(idA), Number(idB), deptId);
      setResult(res);
    } catch (e) { console.error(e); } finally { setLoading(false); }
  };`;

const tabCompNew = `function TabComparativo({ ano, deptId }: { ano: number; deptId: number }) {
  const [versoesDespesas, setVersoesDespesas] = useState<any[]>([]);
  const [versoesVendas, setVersoesVendas] = useState<any[]>([]);
  const [tipo, setTipo] = useState("DESPESAS");
  const [idA, setIdA] = useState<string>("");
  const [idB, setIdB] = useState<string>("");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    orcamentoService.listarVersoes(ano, "DESPESAS", deptId).then(setVersoesDespesas).catch(() => { });
    orcamentoService.listarVersoes(ano, "VENDAS", deptId).then(setVersoesVendas).catch(() => { });
  }, [ano, deptId]);

  const versoes = tipo === "DESPESAS" ? versoesDespesas : versoesVendas;
  const getProdNome = (id: number) => result?.produtos_map?.[id] || id;
  const getPlanoNome = (id: number) => result?.planos_map?.[id] || id;

  const comparar = async () => {
    if (!idA || !idB) return;
    setLoading(true);
    try {
      const res = await (orcamentoService as any).getComparativo(idA, idB, tipo, ano, deptId, false);
      setResult(res);
    } catch (e) { console.error(e); } finally { setLoading(false); }
  };`;

c = c.replace(tabCompOld, tabCompNew);

const selectAOld = `          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Versão A (Base)</label>
            <select value={idA} onChange={e => setIdA(e.target.value ? Number(e.target.value) : "")}
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white text-slate-700">
              <option value="">Selecione...</option>
              {versoes.map(v => <option key={v.id} value={v.id}>{v.descricao}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Versão B (Comparação)</label>
            <select value={idB} onChange={e => setIdB(e.target.value ? Number(e.target.value) : "")}
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white text-slate-700">
              <option value="">Selecione...</option>
              {versoes.map(v => <option key={v.id} value={v.id}>{v.descricao}</option>)}
            </select>
          </div>`;

const selectANew = `          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Versão A (Base)</label>
            <select value={idA} onChange={e => setIdA(e.target.value)}
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white text-slate-700">
              <option value="">Selecione...</option>
              {versoes.map(v => <option key={v.id} value={v.descricao}>{v.descricao}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Versão B (Comparação)</label>
            <select value={idB} onChange={e => setIdB(e.target.value)}
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white text-slate-700">
              <option value="">Selecione...</option>
              {versoes.map(v => <option key={v.id} value={v.descricao}>{v.descricao}</option>)}
            </select>
          </div>`;

c = c.replace(selectAOld, selectANew);

fs.writeFileSync(FILE, c, 'utf8');
console.log("Done part 3.");
