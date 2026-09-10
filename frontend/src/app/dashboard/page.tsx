"use client";

import React from "react";
import Image from "next/image";

export default function DashboardHome() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center h-full min-h-[60vh]">
      {/* 
        Para um recorte limpo usando apenas CSS, usamos um container wrapper
        que esconde a metade superior (onde está a logo da Moura Leite).
      */}
      <div 
        className="relative w-[500px] h-[250px] overflow-hidden opacity-90 hover:opacity-100 transition-opacity flex items-end justify-center"
      >
        {/* A imagem original será mantida em seu aspect-ratio, mas nós a empurramos para baixo para esconder o topo */}
        <div className="relative w-[500px] h-[500px] -mb-[0px] -mt-[250px]">
          <Image 
            src="/logo-ml-orion.png" 
            alt="ML Órion" 
            fill
            className="object-contain object-bottom"
            priority
          />
        </div>
      </div>
      
      <h2 className="mt-8 text-2xl font-semibold text-slate-400 tracking-wider">
        Bem-vindo ao ML Órion
      </h2>
    </div>
  );
}
