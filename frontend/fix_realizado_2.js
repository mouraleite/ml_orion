const fs = require('fs');
const FILE = 'c:/Users/Usuario/Desktop/Em Desenvolvimento/Meus Projetos/ERP ML/frontend/src/app/dashboard/orcamento/realizado/page.tsx';
let c = fs.readFileSync(FILE, 'utf8');

const rpStateOld = `// Novos estados dos filtros avançados
  const [filtroMesesAtivo, setFiltroMesesAtivo] = useState(false);
  const [mesesSelecionados, setMesesSelecionados] = useState<string[]>(MESES);
  const [busca, setBusca] = useState("");
  const [idCentroCusto, setIdCentroCusto] = useState("Todos");
  const [produtoFiltro, setProdutoFiltro] = useState("Todos");
  const [planoFinanceiro, setPlanoFinanceiro] = useState("Todos");
  const [idEmpresa, setIdEmpresa] = useState("Todos");
  const [empresaFiltro, setEmpresaFiltro] = useState("Todas");

  const { user } = useAuth();
  const deptId = user?.departamento_id || 1;

  // Opções carregadas do backend
  const [opcoesCentrosCusto, setOpcoesCentrosCusto] = useState<any[]>([]);
  const [opcoesPlanos, setOpcoesPlanos] = useState<any[]>([]);
  const [opcoesEmpresas, setOpcoesEmpresas] = useState<any[]>([]);

  useEffect(() => {
    async function loadFiltros() {
      try {
        const [ccs, planos, emps] = await Promise.all([
          apoioService.getCentrosCusto(),
          apoioService.getPlanosFinanceiros(),
          apoioService.getEmpresas()
        ]);
        setOpcoesCentrosCusto(ccs || []);
        setOpcoesPlanos(planos || []);
        setOpcoesEmpresas(emps || []);
      } catch (err) {
        console.error("Erro ao carregar filtros avançados:", err);
      }
    }
    loadFiltros();
  }, []);`;

const rpStateNew = `// Novos estados dos filtros avançados
  const [filtroMesesAtivo, setFiltroMesesAtivo] = useState(false);
  const [mesesSelecionados, setMesesSelecionados] = useState<string[]>(MESES);
  const [busca, setBusca] = useState("");
  const [idCentroCusto, setIdCentroCusto] = useState<string[]>([]);
  const [produtoFiltro, setProdutoFiltro] = useState<string[]>([]);
  const [planoFinanceiro, setPlanoFinanceiro] = useState<string[]>([]);
  const [idEmpresa, setIdEmpresa] = useState<string[]>([]);
  const [empresaFiltro, setEmpresaFiltro] = useState<string[]>([]);

  const { user } = useAuth();
  const deptId = user?.departamento_id || 1;

  // Opções carregadas do backend
  const [centrosCustoBase, setCentrosCustoBase] = useState<any[]>([]);
  const [opcoesCentrosCusto, setOpcoesCentrosCusto] = useState<any[]>([]);
  const [opcoesPlanos, setOpcoesPlanos] = useState<any[]>([]);
  const [opcoesEmpresas, setOpcoesEmpresas] = useState<any[]>([]);

  useEffect(() => {
    async function loadFiltros() {
      try {
        const res = await apoioService.getFiltrosAtivos(ano);
        setCentrosCustoBase(res.centros_custo || []);
        setOpcoesCentrosCusto(res.centros_custo || []);
        setOpcoesPlanos(res.planos_financeiros || []);
        setOpcoesEmpresas(res.empresas || []);
      } catch (err) {
        console.error("Erro ao carregar filtros avançados:", err);
      }
    }
    loadFiltros();
  }, [ano]);
  
  const filtroOpcoes = React.useMemo(() => {
    const centrosId = opcoesCentrosCusto.map((p: any) => p.id_sienge || String(p.id)).filter(Boolean);
    const produtos = Array.from(new Set(opcoesCentrosCusto.map((p: any) => parseCentroNome(p.nome).produto)));
    const plans = Array.from(new Set(opcoesPlanos.map((p: any) => p.nome || p.name)));
    const empresasId = Array.from(new Set(opcoesCentrosCusto.map((p: any) => p.id_empresa))).filter(Boolean);
    const empresasNome = Array.from(new Set(opcoesCentrosCusto.map((p: any) => p.nome_empresa))).filter(Boolean).sort();
    const empresasNomeUniq = Array.from(new Set(empresasNome)).sort();
    return {
      centrosId: centrosId.sort((a: any, b: any) => Number(a) - Number(b)).map((id: any) => ({ value: String(id), label: String(id) })),
      produtos: produtos.map((p: any) => ({ value: String(p), label: String(p) })),
      planos: plans.map((p: any) => ({ value: String(p), label: String(p) })),
      empresasId: empresasId.map((e: any) => ({ value: String(e), label: String(e) })),
      empresasNome: empresasNomeUniq.map((e: any) => ({ value: String(e), label: String(e) })),
    };
  }, [opcoesCentrosCusto, opcoesPlanos, opcoesEmpresas]);`;

c = c.replace(rpStateOld, rpStateNew);

const rpJsxOld = `        {/* Busca e ID Centro Custo */}
        <div className="flex flex-col md:flex-row gap-4 items-end">
          <div className="flex-1 min-w-[200px]">
            <label className="block text-xs font-semibold text-slate-600 mb-1.5">Busca</label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="text"
                placeholder="Buscar por nome ou ID..."
                value={busca}
                onChange={e => setBusca(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-sm border border-slate-200 rounded-lg bg-white text-slate-700 focus:outline-none focus:border-ml-green focus:ring-1 focus:ring-ml-green/20"
              />
            </div>
          </div>

          <div className="flex-1 min-w-[150px]">
            <label className="block text-xs font-semibold text-slate-600 mb-1.5">ID Centro de Custo</label>
            <select
              value={idCentroCusto}
              onChange={e => setIdCentroCusto(e.target.value)}
              className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 bg-white text-slate-700 focus:outline-none focus:border-ml-green focus:ring-1 focus:ring-ml-green/20"
            >
              <option value="Todos">Todos</option>
              {opcoesCentrosCusto.map(cc => (
                <option key={cc.db_id || cc.id} value={cc.db_id || cc.id}>{cc.id || cc.codigo}</option>
              ))}
            </select>
          </div>

          <div className="flex-1 min-w-[150px]">
            <label className="block text-xs font-semibold text-slate-600 mb-1.5">Produto</label>
            <select
              value={produtoFiltro}
              onChange={e => setProdutoFiltro(e.target.value)}
              className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 bg-white text-slate-700 focus:outline-none focus:border-ml-green focus:ring-1 focus:ring-ml-green/20"
            >
              <option value="Todos">Todos</option>
              {opcoesCentrosCusto.map(cc => (
                <option key={\`prod-\${cc.db_id || cc.id}\`} value={cc.db_id || cc.id}>{cc.nome || cc.descricao}</option>
              ))}
            </select>
          </div>

          <div className="flex-1 min-w-[150px]">
            <label className="block text-xs font-semibold text-slate-600 mb-1.5">Plano Financeiro</label>
            <select
              value={planoFinanceiro}
              onChange={e => setPlanoFinanceiro(e.target.value)}
              className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 bg-white text-slate-700 focus:outline-none focus:border-ml-green focus:ring-1 focus:ring-ml-green/20"
            >
              <option value="Todos">Todos</option>
              {opcoesPlanos.map(pf => (
                <option key={pf.id} value={pf.id}>{pf.nome || pf.name}</option>
              ))}
            </select>
          </div>

          <div className="flex-1 min-w-[150px]">
            <label className="block text-xs font-semibold text-slate-600 mb-1.5">ID Empresa</label>
            <select
              value={idEmpresa}
              onChange={e => setIdEmpresa(e.target.value)}
              className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 bg-white text-slate-700 focus:outline-none focus:border-ml-green focus:ring-1 focus:ring-ml-green/20"
            >
              <option value="Todos">Todos</option>
              {opcoesEmpresas.map(emp => (
                <option key={emp.id} value={emp.id}>{emp.id}</option>
              ))}
            </select>
          </div>

          <div className="flex-1 min-w-[150px]">
            <label className="block text-xs font-semibold text-slate-600 mb-1.5">Empresa</label>
            <select
              value={empresaFiltro}
              onChange={e => setEmpresaFiltro(e.target.value)}
              className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 bg-white text-slate-700 focus:outline-none focus:border-ml-green focus:ring-1 focus:ring-ml-green/20"
            >
              <option value="Todas">Todas</option>
              {opcoesEmpresas.map(emp => (
                <option key={\`emp-\${emp.id}\`} value={emp.id}>{emp.nome || emp.name || emp.descricao}</option>
              ))}
            </select>
          </div>
        </div>`;

const rpJsxNew = `        {/* Busca e ID Centro Custo */}
        <div className="flex flex-col md:flex-row gap-4 items-end">
          <div className="flex-1 min-w-[200px]">
            <label className="block text-xs font-semibold text-slate-600 mb-1.5">Busca</label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="text"
                placeholder="Buscar por nome ou ID..."
                value={busca}
                onChange={e => setBusca(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-sm border border-slate-200 rounded-lg bg-white text-slate-700 focus:outline-none focus:border-ml-green focus:ring-1 focus:ring-ml-green/20 h-[38px]"
              />
            </div>
          </div>

          <div className="flex-1 min-w-[150px]">
            <MultiSelect label="ID Centro de Custo"
              options={filtroOpcoes.centrosId}
              value={idCentroCusto}
              onChange={setIdCentroCusto}
              placeholder="Todos"
            />
          </div>

          <div className="flex-1 min-w-[150px]">
            <MultiSelect label="Produto"
              options={filtroOpcoes.produtos}
              value={produtoFiltro}
              onChange={setProdutoFiltro}
              placeholder="Todos"
            />
          </div>

          <div className="flex-1 min-w-[150px]">
            <MultiSelect label="Plano Financeiro"
              options={filtroOpcoes.planos}
              value={planoFinanceiro}
              onChange={setPlanoFinanceiro}
              placeholder="Todos"
            />
          </div>

          <div className="flex-1 min-w-[150px]">
            <MultiSelect label="ID Empresa"
              options={filtroOpcoes.empresasId}
              value={idEmpresa}
              onChange={setIdEmpresa}
              placeholder="Todos"
            />
          </div>

          <div className="flex-1 min-w-[150px]">
            <MultiSelect label="Empresa"
              options={filtroOpcoes.empresasNome}
              value={empresaFiltro}
              onChange={setEmpresaFiltro}
              placeholder="Todas"
            />
          </div>
        </div>`;

c = c.replace(rpJsxOld, rpJsxNew);

const passOld = `          {tab === "despesas" && <TabDespesasReceitas ano={ano} tipo="DESPESAS" consolidado={consolidado} deptId={deptId} filtros={{ busca, idCentroCusto, produtoFiltro, planoFinanceiro, idEmpresa, empresaFiltro, filtroMesesAtivo, mesesSelecionados }} />}
          {tab === "receitas" && <TabDespesasReceitas ano={ano} tipo="RECEITAS" consolidado={consolidado} deptId={deptId} filtros={{ busca, idCentroCusto, produtoFiltro, planoFinanceiro, idEmpresa, empresaFiltro, filtroMesesAtivo, mesesSelecionados }} />}
          {tab === "vendas" && <TabVendas ano={ano} consolidado={consolidado} deptId={deptId} filtros={{ busca, idCentroCusto, produtoFiltro, planoFinanceiro, idEmpresa, empresaFiltro, filtroMesesAtivo, mesesSelecionados }} />}
          {tab === "comparativo" && <TabComparativo ano={ano} deptId={deptId} />}`;

const passNew = `          {tab === "despesas" && <TabDespesasReceitas ano={ano} tipo="DESPESAS" consolidado={consolidado} deptId={deptId} filtros={{ busca, idCentroCusto, produtoFiltro, planoFinanceiro, idEmpresa, empresaFiltro, filtroMesesAtivo, mesesSelecionados, centrosCustoBase }} />}
          {tab === "receitas" && <TabDespesasReceitas ano={ano} tipo="RECEITAS" consolidado={consolidado} deptId={deptId} filtros={{ busca, idCentroCusto, produtoFiltro, planoFinanceiro, idEmpresa, empresaFiltro, filtroMesesAtivo, mesesSelecionados, centrosCustoBase }} />}
          {tab === "vendas" && <TabVendas ano={ano} consolidado={consolidado} deptId={deptId} filtros={{ busca, idCentroCusto, produtoFiltro, planoFinanceiro, idEmpresa, empresaFiltro, filtroMesesAtivo, mesesSelecionados, centrosCustoBase }} />}
          {tab === "comparativo" && <TabComparativo ano={ano} deptId={deptId} />}`;

c = c.replace(passOld, passNew);

fs.writeFileSync(FILE, c, 'utf8');
console.log("Done part 2.");
