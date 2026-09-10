import React from "react";

interface FormattedNumberProps extends React.HTMLAttributes<HTMLSpanElement> {
  value: number;
  format?: "currency" | "percent" | "decimal" | "integer";
  decimals?: number;
  colorize?: boolean; // Define se deve colorir baseado em positivo/negativo
  inverseColorLogic?: boolean; // Se true, positivo fica vermelho e negativo fica verde (ex: Custos)
  divisor?: number; // Ex: 1000 para milhares, 1000000 para milhões
  suffix?: string; // Ex: "k", " mi", " bi"
}

export function FormattedNumber({
  value,
  format = "decimal",
  decimals = 2,
  colorize = true,
  inverseColorLogic = false,
  divisor = 1,
  suffix = "",
  className = "",
  ...props
}: FormattedNumberProps) {
  let formattedValue = "";
  
  // Aplica o divisor antes de formatar
  const scaledValue = value / divisor;

  // Formatação de acordo com o padrão brasileiro
  switch (format) {
    case "currency":
    case "decimal":
      // Ambos usam o mesmo estilo numérico (1.000.000,00) sem o símbolo de moeda
      formattedValue = new Intl.NumberFormat("pt-BR", {
        style: "decimal",
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      }).format(scaledValue) + suffix;
      break;
    case "percent":
      // Assume que o valor recebido é o percentual em si (ex: 5.5 = 5,50%)
      formattedValue =
        new Intl.NumberFormat("pt-BR", {
          minimumFractionDigits: decimals,
          maximumFractionDigits: decimals,
        }).format(scaledValue) + "%" + suffix;
      break;
    case "integer":
      formattedValue = new Intl.NumberFormat("pt-BR", {
        maximumFractionDigits: 0,
      }).format(scaledValue) + suffix;
      break;
    default:
      formattedValue = new Intl.NumberFormat("pt-BR", {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      }).format(scaledValue) + suffix;
      break;
  }

  // Lógica de Cores
  let colorClass = "";
  if (colorize) {
    if (value < 0) {
      // Cores mais vibrantes adaptadas para o modo escuro (background ml-surface)
      colorClass = inverseColorLogic ? "text-emerald-400" : "text-red-400";
    } else if (value > 0) {
      colorClass = inverseColorLogic ? "text-red-400" : "text-emerald-400";
    }
  }

  return (
    <span className={`${colorClass} font-medium ${className}`} {...props}>
      {formattedValue}
    </span>
  );
}

