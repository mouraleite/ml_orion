"use client";
import React, { useState } from "react";
import { createPortal } from "react-dom";
import ProtectedRoute from "@/components/ProtectedRoute";
import { useAuth } from"@/contexts/AuthContext";
import { LogOut, ChevronDown, ChevronRight, Menu, Save, Loader2, Shield } from "lucide-react";
import { AppLoadingScreen } from "@/components/shared/BudgetLoadingState";
import Link from"next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { APP_VERSION } from "@/version";
import { api } from "@/lib/api";
import { canSeeFullMenu, canWriteModule } from "@/lib/roles";
import { isPlaceholderHref } from "@/lib/productModules";
import { MENU_MODULES } from "@/lib/menuCatalog";
import { filterMenuModules, isPathAllowed, matchMenuPath } from "@/lib/accessMatrix";

import Image from"next/image";

function PlaceholderBadge({ variant = "sidebar" }: { variant?: "sidebar" | "flyout" }) {
  const classes =
    variant === "sidebar"
      ? "text-[9px] uppercase tracking-wide px-1.5 py-0.5 rounded bg-ml-orange/25 text-ml-orange shrink-0"
      : "text-[9px] uppercase tracking-wide px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 shrink-0";
  return <span className={classes}>Em breve</span>;
}

function DashboardLayoutInner({
 children,
}: {
 children: React.ReactNode;
}) {
 const { user, logout } = useAuth();
 const pathname = usePathname();
 const sheetScroll = pathname === "/dashboard/orcamento/analitico-gastos-2";
 const searchParams = useSearchParams();
 const [expandedModules, setExpandedModules] = useState<string[]>([]);
 const [expandedSubModules, setExpandedSubModules] = useState<string[]>([]);
 const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
 const [isSavingVersion, setIsSavingVersion] = useState(false);
 const [flyoutState, setFlyoutState] = useState<{ show: boolean, top: number, items: any[], name: string } | null>(null);
 const flyoutTimeout = React.useRef<NodeJS.Timeout | null>(null);

  const handleMouseEnterItem = (e: React.MouseEvent, item: any) => {
    if (flyoutTimeout.current) clearTimeout(flyoutTimeout.current);
    const rect = e.currentTarget.getBoundingClientRect();
    const windowHeight = window.innerHeight;
    
    const estimatedHeight = 30 + (item.subItems.length * 40) + 16;
    let adjustedTop = rect.top;
    
    if (rect.top + estimatedHeight > windowHeight - 20) {
      adjustedTop = windowHeight - estimatedHeight - 20;
    }
    if (adjustedTop < 20) adjustedTop = 20;

    setFlyoutState({ show: true, top: adjustedTop, items: item.subItems, name: item.name });
  };

 const handleMouseLeaveItem = () => {
   flyoutTimeout.current = setTimeout(() => setFlyoutState(null), 300);
 };

 const handleSaveVersion = async () => {
   try {
     setIsSavingVersion(true);
     const { data } = await api.post("/system/version");
     alert(
       `Versão ${data.version} salva. O arquivo Backups/ERP_ML_ultimo.zip foi atualizado (sempre o mesmo arquivo).`
     );
     setTimeout(() => window.location.reload(), 500);
   } catch (error) {
     alert("Falha ao salvar versão.");
   } finally {
     setIsSavingVersion(false);
   }
 };

 const toggleModule = (moduleId: string) => {
 if (isSidebarCollapsed) {
 setIsSidebarCollapsed(false);
 // Se estava recolhido, ao clicar num módulo, além de abrir a barra lateral, garante que o módulo abre
 if (!expandedModules.includes(moduleId)) {
 setExpandedModules(prev => [...prev, moduleId]);
 }
 } else {
 setExpandedModules(prev => 
 prev.includes(moduleId) ? prev.filter(id => id !== moduleId) : [...prev, moduleId]
 );
 }
 };

 const toggleSubModule = (subName: string) => {
   setExpandedSubModules(prev => 
     prev.includes(subName) ? prev.filter(n => n !== subName) : [...prev, subName]
   );
 };

  const filteredModules = React.useMemo(() => {
    if (!user) return [];
    if (canSeeFullMenu(user)) return MENU_MODULES;
    if (!user.perfil || !user.perfil.permissions) return [];
    return filterMenuModules(MENU_MODULES, user.perfil.permissions);
  }, [user]);

  const canOpenCurrentScreen = React.useMemo(() => {
    if (!user) return false;
    if (canSeeFullMenu(user)) return true;
    return isPathAllowed(user.perfil?.permissions, pathname, searchParams);
  }, [user, pathname, searchParams]);

  const currentWrite = React.useMemo(() => {
    if (!user) return true;
    const hit = matchMenuPath(pathname, searchParams);
    if (!hit) return true;
    return canWriteModule(user, hit.moduleTitle);
  }, [user, pathname, searchParams]);

 return (
 <ProtectedRoute>
 <div className="min-h-screen bg-slate-50 flex font-sans print:bg-white">
 
 {/* Sidebar Única */}
 <aside className={`${isSidebarCollapsed ?"w-20" :"w-72"} bg-ml-very-dark text-white flex flex-col shrink-0 hidden md:flex z-30 shadow-xl transition-all duration-300 ease-in-out relative print:hidden`}>
 
 {/* Cabeçalho da Sidebar (Logo) */}
 <div className="h-20 flex items-center justify-center px-6 border-b border-white/5 bg-ml-very-dark shrink-0 overflow-hidden relative">
 <div className={`transition-opacity duration-300 ${isSidebarCollapsed ?"opacity-0 w-0" :"opacity-100"}`}>
 <Link href="/dashboard">
 <Image 
 src="/logo-moura-branco.png" 
 alt="Moura Leite" 
 width={180} 
 height={60} 
 className="w-auto h-12 object-contain"
 priority
 />
 </Link>
 </div>
 
 {/* Ícone menor para quando recolhido */}
 <div className={`absolute left-1/2 -translate-x-1/2 transition-opacity duration-300 ${isSidebarCollapsed ?"opacity-100" :"opacity-0 pointer-events-none"}`}>
 <div className="w-12 h-12 shrink-0 flex items-center justify-center p-1">
 <Link href="/dashboard">
 <Image 
 src="/logo-moura-branco.png" 
 alt="Moura Leite" 
 width={48} 
 height={48} 
 className="w-full h-full object-contain"
 priority
 />
 </Link>
 </div>
 </div>
 </div>

 {/* Navegação */}
 <nav className="flex-1 overflow-y-auto py-4 overflow-x-hidden scrollbar-thin scrollbar-thumb-ml-green scrollbar-track-transparent">
 <div className={`px-4 mb-2 transition-opacity duration-300 ${isSidebarCollapsed ?"opacity-0 h-0 overflow-hidden" :"opacity-100"}`}>
 <p className="text-xs font-semibold text-white/40 uppercase tracking-wider mb-2 px-2 whitespace-nowrap">Menu Principal</p>
 </div>
 {filteredModules.map((mod) => {
 const isExpanded = expandedModules.includes(mod.id);
 return (
 <div key={mod.id} className="mb-1">
 <button
 onClick={() => toggleModule(mod.id)}
 title={isSidebarCollapsed ? mod.title : undefined}
 className={`w-full flex items-center ${isSidebarCollapsed ?"justify-center" :"justify-between"} px-6 py-3 transition-all duration-200 ${
 isExpanded && !isSidebarCollapsed
 ?"bg-ml-green/20 border-l-2 border-ml-orange" 
 :"border-l-2 border-transparent hover:bg-ml-green/10"
 }`}
 >
 <div className="flex items-center gap-3">
 <mod.icon className={`w-5 h-5 shrink-0 transition-colors ${isExpanded && !isSidebarCollapsed ?"text-ml-orange" :"text-white/60"}`} />
 <span className={`font-semibold text-sm transition-all duration-300 whitespace-nowrap ${isExpanded ?"text-white" :"text-white/80"} ${isSidebarCollapsed ?"opacity-0 w-0" :"opacity-100"}`}>
 {mod.title}
 </span>
 </div>
 {!isSidebarCollapsed && (
 isExpanded ? (
 <ChevronDown className="w-4 h-4 text-white/50 shrink-0" />
 ) : (
 <ChevronRight className="w-4 h-4 text-white/50 shrink-0" />
 )
 )}
 </button>
 
 {/* Sub-itens com animação CSS */}
 {isExpanded && !isSidebarCollapsed && (
    <div className="px-4 pb-2 pt-1 space-y-1 bg-ml-dark/50">
      {mod.items.map((item) => {
        const hasSubItems = item.subItems && item.subItems.length > 0;
        const menuHit = matchMenuPath(pathname, searchParams);
        const isActive = !hasSubItems && menuHit?.pathname === item.href;

        return (
          <div key={item.name} className="flex flex-col gap-1 relative">
            {hasSubItems ? (
              <button
                onMouseEnter={(e) => handleMouseEnterItem(e, item)}
                onMouseLeave={handleMouseLeaveItem}
                className={`w-full group flex items-center justify-between px-4 py-2.5 rounded-lg text-sm transition-all duration-200 text-white/60 hover:bg-white/10 hover:text-white ${flyoutState?.name === item.name ? "bg-white/10 text-white" : ""}`}
              >
                <div className="flex items-center gap-3">
                  <div className={`w-1.5 h-1.5 shrink-0 rounded-full transition-colors bg-transparent group-hover:bg-white/30 ${flyoutState?.name === item.name ? "!bg-white/30" : ""}`}></div>
                  <span className="whitespace-normal leading-tight text-left">{item.name}</span>
                </div>
                <ChevronRight className={`w-4 h-4 shrink-0 transition-transform ${flyoutState?.name === item.name ? "translate-x-1 text-ml-orange" : ""}`} />
              </button>
            ) : (
              <Link
                href={item.href}
                className={`group flex items-center justify-between px-4 py-2.5 rounded-lg text-sm transition-all duration-200 ${
                  isActive 
                  ?"bg-ml-green text-white font-medium shadow-md border border-white/5" 
                  :"text-white/60 hover:bg-white/10 hover:text-white"
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className={`w-1.5 h-1.5 shrink-0 rounded-full transition-colors ${isActive ?"bg-ml-orange" :"bg-transparent group-hover:bg-white/30"}`}></div>
                  <span className="whitespace-normal leading-tight text-left">{item.name}</span>
                </div>
                {isPlaceholderHref(item.href) && <PlaceholderBadge />}
              </Link>
            )}
          </div>
        );
      })}
    </div>
  )}
 </div>
 );
 })}
 </nav>

 {/* Rodapé da Sidebar (Logout) */}
 <div className="p-4 border-t border-ml-green/30 shrink-0 overflow-hidden flex flex-col gap-2">
   {!isSidebarCollapsed && (
     <div className="flex items-center justify-between px-4 py-2 bg-ml-green/10 rounded-lg border border-ml-green/20">
       <span className="text-xs font-semibold text-white/60">Versão: <span className="text-white">v{APP_VERSION}</span></span>
       <button 
         onClick={handleSaveVersion} 
         disabled={isSavingVersion}
         title="Salvar e empacotar nova versão"
         className="text-white/60 hover:text-ml-orange transition-colors"
       >
         {isSavingVersion ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
       </button>
     </div>
   )}
   <button 
   onClick={logout} 
   title={isSidebarCollapsed ?"Sair do Sistema" : undefined}
   className={`flex items-center gap-3 py-3 text-sm font-medium text-red-300 hover:bg-red-500/10 hover:text-red-200 rounded-lg transition-colors whitespace-nowrap ${isSidebarCollapsed ?"px-2 justify-center w-auto" :"px-4 w-full"}`}
   >
    <LogOut className="w-5 h-5 shrink-0" />
    <span className={`font-medium transition-all duration-300 ${isSidebarCollapsed ?"opacity-0 w-0" :"opacity-100"}`}>Sair</span>
    </button>
  </div>
  
  {/* FLYOUT MENU — portal evita ficar atrás de sticky headers / matrizes (z-index local) */}
  {flyoutState?.show && typeof document !== "undefined" && createPortal(
    <div 
      className="fixed bg-white shadow-2xl rounded-r-lg border border-slate-200 z-[9998] py-2 flex flex-col w-56 animate-in fade-in zoom-in-95 duration-150"
      style={{ top: flyoutState.top, left: isSidebarCollapsed ? 80 : 288 }}
      onMouseEnter={() => { if (flyoutTimeout.current) clearTimeout(flyoutTimeout.current); }}
      onMouseLeave={handleMouseLeaveItem}
    >
      <div className="px-4 py-2 text-[11px] font-bold text-slate-400 uppercase tracking-wider border-b border-slate-100 mb-1 mx-2">
        {flyoutState.name}
      </div>
      <div className="px-2 flex flex-col gap-1 mt-1">
        {flyoutState.items.map(sub => {
          const hasQueryId = sub.href.includes("?id=");
          const isSubActive = hasQueryId 
            ? pathname === sub.href.split("?")[0] && searchParams.get("id") === sub.href.split("?id=")[1]
            : pathname === sub.href;
          return (
            <Link
              key={sub.name}
              href={sub.href}
              className={`group flex items-center justify-between px-3 py-2.5 rounded-md text-sm transition-colors ${
                isSubActive 
                ?"text-brand-green bg-green-50/50 font-medium" 
                :"text-slate-600 hover:text-slate-900 hover:bg-slate-50"
              }`}
            >
              <span className="whitespace-normal leading-tight text-left">{sub.name}</span>
              {isPlaceholderHref(sub.href) && <PlaceholderBadge variant="flyout" />}
            </Link>
          );
        })}
      </div>
    </div>,
    document.body,
  )}

 </aside>

 {/* Área de Conteúdo Principal */}
 <div className="flex-1 flex flex-col min-w-0 h-screen overflow-hidden print:h-auto print:overflow-visible">
 
 {/* Cabeçalho Topo (Simplificado) */}
 <header className="h-16 bg-white border-b border-slate-200 flex items-center px-6 justify-between shrink-0 z-10 shadow-sm print:hidden">
 <div className="flex items-center gap-4">
 <button
 onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
 className="p-2 rounded-lg text-slate-500 hover:bg-slate-100 transition-colors hidden md:block"
 >
 <Menu className="w-5 h-5" />
 </button>
 <h2 className="text-lg font-semibold text-slate-800 hidden sm:block">ML Órion</h2>
 </div>
 
 <div className="flex items-center gap-4">
 <div className="flex items-center gap-3 bg-slate-50 px-3 py-1.5 rounded-full border border-slate-200 shadow-sm hover:shadow-md transition-shadow cursor-pointer">
 <span className="text-sm font-medium text-slate-700 hidden sm:block">
 Olá, {user?.full_name?.split(' ')[0] || 'Usuário'}
 </span>
 <div className="w-8 h-8 rounded-full bg-ml-green text-white flex items-center justify-center font-bold text-sm shadow-inner">
 {user?.full_name?.charAt(0) || 'U'}
 </div>
 </div>
 </div>
 </header>

 {/* Main Content Area com scroll */}
 <main className="flex-1 flex flex-col overflow-hidden bg-slate-50 print:overflow-visible print:bg-white">
 <div className={sheetScroll
   ? "flex-1 min-h-0 min-w-0 w-full overflow-auto [container-type:size] print:overflow-visible"
   : "flex-1 min-h-0 min-w-0 overflow-y-auto overflow-x-hidden p-6 md:p-8 w-full flex flex-col print:p-0"
 }>
 {canOpenCurrentScreen ? (
   <>
     {!currentWrite ? (
       <div className={`mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-2.5 text-sm text-amber-900 print:hidden ${sheetScroll ? "sticky left-0 z-20 w-[100cqw] max-w-[100cqw] mx-6 md:mx-8 mt-6" : ""}`}>
         Somente visualização neste módulo. Você não pode criar nem alterar.
       </div>
     ) : null}
     {children}
   </>
 ) : (
   <div className="max-w-lg mx-auto mt-10 bg-white border border-slate-200 rounded-xl p-8 text-center shadow-sm">
     <div className="w-12 h-12 mx-auto mb-4 rounded-lg bg-slate-100 flex items-center justify-center text-slate-500">
       <Shield className="w-6 h-6" />
     </div>
     <h1 className="text-lg font-semibold text-slate-800">Acesso não liberado</h1>
     <p className="text-sm text-slate-500 mt-2">
       Seu perfil não inclui esta tela. Peça ao administrador para marcá-la em Perfis de Acesso.
     </p>
     <Link href="/dashboard" className="inline-block mt-5 text-sm font-medium text-ml-green hover:underline">
       Voltar ao início
     </Link>
   </div>
 )}
 </div>
 </main>
 </div>
 </div>
 </ProtectedRoute>
 );
}

export default function DashboardLayout({
 children,
}: {
 children: React.ReactNode;
}) {
  return (
    <React.Suspense fallback={<AppLoadingScreen />}>
      <DashboardLayoutInner>{children}</DashboardLayoutInner>
    </React.Suspense>
  );
}
