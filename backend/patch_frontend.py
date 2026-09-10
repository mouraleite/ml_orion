import re

with open('c:/Users/Usuario/Desktop/Em Desenvolvimento/Meus Projetos/ERP ML/frontend/src/components/viabilities/SummaryTab.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Update multiplier logic: if data.indicators_empreendedor exists, multiplier = 1 for those modes
content = content.replace(
    'const multiplier = getMultiplier();',
    'const multiplier = (viewMode !== "Global" && (data as any).indicators_empreendedor) ? 1 : getMultiplier();'
)

# Update allColumns to use ind_empreendedor and monthly_cashflow_empreendedor
allColumns_orig = """  const allColumns = [
      {
          id: "current",
          title: "CENÁRIO ATUAL",
          isCurrent: true,
          ind: data.indicators,
          phys: physicalData,
          dates: datesData,
          monthly_cashflow: data.monthly_cashflow || []
      },"""

allColumns_new = """  const allColumns = [
      {
          id: "current",
          title: "CENÁRIO ATUAL",
          isCurrent: true,
          ind: viewMode === "Empreendedor" && (data as any).indicators_empreendedor ? (data as any).indicators_empreendedor : data.indicators,
          phys: physicalData,
          dates: datesData,
          monthly_cashflow: viewMode === "Empreendedor" && (data as any).monthly_cashflow_empreendedor ? (data as any).monthly_cashflow_empreendedor : data.monthly_cashflow || []
      },"""

content = content.replace(allColumns_orig, allColumns_new)

# For snapshots
snap_orig = """          ind: s.snapshot_data?.indicators || {},
          phys: s.snapshot_data?.physical_data || {},
          dates: s.snapshot_data?.dates || {},
          monthly_cashflow: s.snapshot_data?.monthly_cashflow || []"""

snap_new = """          ind: viewMode === "Empreendedor" && s.snapshot_data?.indicators_empreendedor ? s.snapshot_data.indicators_empreendedor : (s.snapshot_data?.indicators || {}),
          phys: s.snapshot_data?.physical_data || {},
          dates: s.snapshot_data?.dates || {},
          monthly_cashflow: viewMode === "Empreendedor" && s.snapshot_data?.monthly_cashflow_empreendedor ? s.snapshot_data.monthly_cashflow_empreendedor : (s.snapshot_data?.monthly_cashflow || [])"""

content = content.replace(snap_orig, snap_new)

with open('c:/Users/Usuario/Desktop/Em Desenvolvimento/Meus Projetos/ERP ML/frontend/src/components/viabilities/SummaryTab.tsx', 'w', encoding='utf-8') as f:
    f.write(content)

print('SummaryTab modified!')
