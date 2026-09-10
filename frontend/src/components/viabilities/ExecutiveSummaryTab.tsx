import React, { useState } from 'react';
import { api } from '@/lib/api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { calculateAISimilarity } from '@/lib/similarity';

interface Props {
  viabilityId: number;
  parecerExecutivo: string | null;
  parecerOriginalIa?: string | null;
  onChange: (value: string) => void;
  onSave?: (value: string) => Promise<void>;
}

const ExecutiveSummaryTab: React.FC<Props> = ({ viabilityId, parecerExecutivo, parecerOriginalIa, onChange, onSave }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [apiKey, setApiKey] = useState(localStorage.getItem('GEMINI_API_KEY') || '');
  const [showApiInput, setShowApiInput] = useState(false);
  const [isEditing, setIsEditing] = useState(false);

  const similarityScore = React.useMemo(() => {
    if (!parecerOriginalIa) return null;
    return calculateAISimilarity(parecerOriginalIa, parecerExecutivo);
  }, [parecerOriginalIa, parecerExecutivo]);

  const DISCLAIMER = "\n\n> *Nota: Este parecer foi gerado automaticamente por Inteligência Artificial.*";

  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    let newValue = e.target.value;
    // Se o usuário modificou qualquer coisa e a nota da IA ainda estiver lá, nós a removemos
    if (newValue.includes(DISCLAIMER)) {
      newValue = newValue.replace(DISCLAIMER, "");
    }
    onChange(newValue);
  };

  const handleGenerate = async () => {
    if (!apiKey) {
      setShowApiInput(true);
      setError('Por favor, insira sua chave da API do Gemini.');
      return;
    }
    
    localStorage.setItem('GEMINI_API_KEY', apiKey);
    setLoading(true);
    setError('');
    onChange(''); // Limpa o texto antigo instantaneamente enquanto carrega
    
    try {
      const response = await api.post(`/viabilities/${viabilityId}/generate-summary`, { api_key: apiKey });
      if (response.data && response.data.summary) {
        onChange(response.data.summary);
        if (onSave) {
          await onSave(response.data.summary);
        }
        setIsEditing(false); // Sempre abre o preview após gerar
      }
    } catch (err: any) {
      console.error("Erro ao gerar:", err);
      setError(err.response?.data?.detail || 'Ocorreu um erro ao gerar o resumo.');
    } finally {
      setLoading(false);
    }
  };

  const markdownComponents = {
    table: ({node, ...props}: any) => <div className="overflow-x-auto my-6"><table className="min-w-full divide-y divide-slate-200 border border-slate-200 shadow-sm rounded-lg" {...props} /></div>,
    thead: ({node, ...props}: any) => <thead className="bg-slate-50" {...props} />,
    th: ({node, ...props}: any) => <th className="px-4 py-3 text-left text-xs font-bold text-slate-700 uppercase tracking-wider border-b border-slate-200" {...props} />,
    td: ({node, ...props}: any) => <td className="px-4 py-3 text-sm text-slate-700 border-b border-slate-100" {...props} />,
    h1: ({node, ...props}: any) => <h1 className="text-2xl font-bold text-slate-800 mt-6 mb-4" {...props} />,
    h2: ({node, ...props}: any) => <h2 className="text-xl font-bold text-slate-800 mt-6 mb-3" {...props} />,
    h3: ({node, ...props}: any) => <h3 className="text-lg font-bold text-slate-800 mt-5 mb-2" {...props} />,
    p: ({node, ...props}: any) => <p className="text-slate-600 mb-3 leading-relaxed" {...props} />,
    ul: ({node, ...props}: any) => <ul className="list-disc pl-5 mb-4 text-slate-600 space-y-1" {...props} />,
    ol: ({node, ...props}: any) => <ol className="list-decimal pl-5 mb-4 text-slate-600 space-y-1" {...props} />,
    li: ({node, ...props}: any) => <li className="" {...props} />,
    strong: ({node, ...props}: any) => <strong className="font-bold text-slate-800" {...props} />,
    blockquote: ({node, ...props}: any) => <blockquote className="border-l-4 border-emerald-500 pl-4 italic text-slate-500 my-4 bg-slate-50 py-2 rounded-r" {...props} />
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-xl font-bold text-gray-800">Parecer Executivo</h2>
          <p className="text-sm text-gray-600 mt-1">
            Digite um resumo analítico sobre o projeto ou utilize a Inteligência Artificial (Gemini) para gerar um texto automaticamente comparando os cenários.
          </p>
        </div>
        
        <button
          onClick={handleGenerate}
          disabled={loading}
          className="flex items-center space-x-2 bg-gradient-to-r from-purple-600 to-indigo-600 text-white px-4 py-2 rounded-lg font-medium hover:from-purple-700 hover:to-indigo-700 transition-all shadow-md disabled:opacity-50"
        >
          {loading ? (
            <span className="animate-pulse">✨ Gerando análise...</span>
          ) : (
            <span>✨ Gerar Análise com IA</span>
          )}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg border border-red-200">
          {error}
        </div>
      )}

      {showApiInput && (
        <div className="mb-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Chave de API do Gemini (Google AI Studio)
          </label>
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="AIzaSy..."
            className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
          />
          <p className="text-xs text-gray-500 mt-2">
            Sua chave é salva apenas no seu navegador (localStorage).
          </p>
        </div>
      )}

      <div className="mb-2 flex justify-between items-end">
        <div className="text-sm text-gray-500">
          {isEditing ? (
             "Você está editando manualmente o parecer. Lembre-se de salvar suas alterações."
          ) : (
            similarityScore !== null && (
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${similarityScore > 80 ? 'bg-purple-100 text-purple-800' : similarityScore > 40 ? 'bg-blue-100 text-blue-800' : 'bg-slate-100 text-slate-800'}`}>
                ✨ {similarityScore}% gerado por IA
              </span>
            )
          )}
        </div>
        <div className="flex gap-2">
          {isEditing && onSave && (
            <button
              onClick={async () => {
                setLoading(true);
                try {
                  await onSave(parecerExecutivo || '');
                  setIsEditing(false);
                } catch (e) {
                  console.error(e);
                  setError("Erro ao salvar o parecer.");
                } finally {
                  setLoading(false);
                }
              }}
              disabled={loading}
              className="px-4 py-1.5 text-sm font-medium rounded-md bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm transition-colors disabled:opacity-50"
            >
              Salvar Parecer
            </button>
          )}
          <div className="bg-gray-100 p-1 rounded-lg inline-flex">
            <button
              onClick={() => setIsEditing(false)}
              className={`px-4 py-1.5 text-sm font-medium rounded-md transition-colors ${
                !isEditing ? 'bg-white text-gray-800 shadow-sm' : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              Visualizar
            </button>
            <button
              onClick={() => setIsEditing(true)}
              className={`px-4 py-1.5 text-sm font-medium rounded-md transition-colors ${
                isEditing ? 'bg-white text-gray-800 shadow-sm' : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              Editar Código
            </button>
          </div>
        </div>
      </div>

      {isEditing ? (
        <textarea
          value={parecerExecutivo || ''}
          onChange={handleTextChange}
          placeholder="Escreva seu resumo executivo aqui..."
          className="w-full h-[500px] p-4 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent font-mono text-sm resize-y"
        />
      ) : (
        <div className="w-full min-h-[500px] p-6 border border-gray-300 rounded-lg bg-white overflow-auto">
          {parecerExecutivo ? (
            <div>
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                {parecerExecutivo}
              </ReactMarkdown>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center text-gray-400 italic">
              Nenhum parecer gerado ainda. Clique em "Gerar Análise com IA" ou mude para o modo "Editar Código".
            </div>
          )}
        </div>
      )}
      
      <div className="mt-4 p-4 bg-blue-50 text-blue-800 rounded-lg text-sm flex items-start">
        <svg className="w-5 h-5 mr-3 mt-0.5 text-blue-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <div>
          <strong>Dica:</strong> Se o relatório possuir conteúdo neste campo, ele será automaticamente impresso como a primeira seção do PDF do Estudo de Viabilidade (seguindo o padrão do relatório Moura Leite).
        </div>
      </div>
    </div>
  );
};

export default ExecutiveSummaryTab;
