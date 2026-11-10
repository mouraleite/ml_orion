"""Busca única no Sienge durante o sync (passo 5 da análise de 09/11/2026).

Antes: cada centro de custo fazia ~34 buscas bulk (pagamentos, recebimentos,
15 anos de previsão, vencidos). Agora, dentro de `busca_unica()`, uma URL com
`costCentersId=X` vira a mesma URL SEM o filtro, buscada UMA vez para a empresa
toda. Os itens são repartidos em arquivos temporários por centro de custo (todo
`costCenterId` que aparece no item, em qualquer nível), e cada CC lê só a sua
parte. Os parsers do sync continuam fazendo o rateio exatamente como antes.

Comparação feita em 09/11/2026 com 24 centros de custo (comparar_busca_unica.py):
289.221 lançamentos iguais nos dois modos, zero diferenças; 34 buscas contra 816.

Memória: o Bulk Data ignora limit/offset e devolve o período inteiro numa resposta
só (sonda de 10/11/2026: contas a receber de 2027 da empresa toda = 287 MB de JSON,
~1 GB ao ler; o ensaio chegou a 2,3 GB). Por isso a busca global é feita MÊS A MÊS
(jan/2027 = 24 MB, ~90 MB ao ler, o mesmo de um CC grande no modo antigo) e cada
resposta é repartida e gravada em disco antes da próxima.
Disco: cada bloco é compactado (zlib). No ensaio de 10/11/2026 com os 311 CCs,
sem compactar, o disco temporário chegou a ~2 GB (item rateado entre muitos CCs
é gravado uma vez em cada um).
"""
from __future__ import annotations

import hashlib
import logging
import os
import pickle
import re
import shutil
import tempfile
import zlib
from contextlib import contextmanager
from datetime import date, timedelta
from typing import Any, Callable, Iterable, Iterator, Optional

logger = logging.getLogger(__name__)

_FILTRO_CC = re.compile(r"[&?]costCentersId=([^&]*)")
_DATA = re.compile(r"([&?])(startDate|endDate)=(\d{4}-\d{2}-\d{2})")


def janelas_mensais(url: str) -> list[str]:
    """Divide uma URL com startDate/endDate em URLs de no máximo um mês-calendário.

    As janelas são contíguas e não se sobrepõem (dia a dia, inclusive nas pontas),
    então a união dos itens é exatamente a do período original.
    """
    datas = {m.group(2): m.group(3) for m in _DATA.finditer(url)}
    if "startDate" not in datas or "endDate" not in datas:
        return [url]
    ini = date.fromisoformat(datas["startDate"])
    fim = date.fromisoformat(datas["endDate"])
    if fim < ini or (ini.year, ini.month) == (fim.year, fim.month):
        return [url]
    urls = []
    atual = ini
    while atual <= fim:
        prox_mes = date(atual.year + (atual.month == 12), atual.month % 12 + 1, 1)
        fim_janela = min(fim, prox_mes - timedelta(days=1))
        u = _DATA.sub(
            lambda m: f"{m.group(1)}{m.group(2)}={(atual if m.group(2) == 'startDate' else fim_janela).isoformat()}",
            url,
        )
        urls.append(u)
        atual = fim_janela + timedelta(days=1)
    return urls


def url_sem_filtro_de_cc(url: str) -> tuple[str, Optional[str]]:
    """(URL sem costCentersId, id do CC filtrado ou None)."""
    m = _FILTRO_CC.search(url)
    if not m:
        return url, None
    cc = m.group(1)
    sem = url[: m.start()] + ("?" if url[m.start()] == "?" else "") + url[m.end():]
    sem = sem.replace("?&", "?")
    if sem.endswith("?"):
        sem = sem[:-1]
    return sem, cc


def ccs_do_item(item: Any) -> set[str]:
    """Todos os costCenterId que aparecem no item, em qualquer nível."""
    achados: set[str] = set()
    pilha = [item]
    while pilha:
        atual = pilha.pop()
        if isinstance(atual, dict):
            for k, v in atual.items():
                if k == "costCenterId" and v not in (None, ""):
                    achados.add(str(v))
                elif isinstance(v, (dict, list)):
                    pilha.append(v)
        elif isinstance(atual, list):
            pilha.extend(atual)
    return achados


class BuscaUnica:
    """Cache de uma rodada do sync. Use via `busca_unica()`."""

    def __init__(self, buscar: Callable[[str], Iterable[list]], pasta: Optional[str] = None):
        self._buscar = buscar
        self._pasta = pasta or tempfile.mkdtemp(prefix="sienge_busca_unica_")
        self._prontas: set[str] = set()
        self._falhas: dict[str, Exception] = {}
        self.buscas_globais = 0

    def _dir(self, url_global: str) -> str:
        return os.path.join(self._pasta, hashlib.sha1(url_global.encode()).hexdigest())

    def _carregar(self, url_global: str) -> None:
        if url_global in self._prontas:
            return
        if url_global in self._falhas:
            # já falhou nesta rodada: não repete a busca (e as tentativas) para cada CC
            raise self._falhas[url_global]
        destino = self._dir(url_global)
        temp = destino + ".parcial"
        shutil.rmtree(temp, ignore_errors=True)
        os.makedirs(temp)
        self.buscas_globais += 1
        try:
            for pagina in (p for janela in janelas_mensais(url_global) for p in self._buscar(janela)):
                por_cc: dict[str, list] = {}
                for item in pagina:
                    for cc in ccs_do_item(item):
                        por_cc.setdefault(cc, []).append(item)
                for cc, itens in por_cc.items():
                    bloco = zlib.compress(pickle.dumps(itens, protocol=pickle.HIGHEST_PROTOCOL), 1)
                    with open(os.path.join(temp, _nome_arquivo(cc)), "ab") as f:
                        f.write(len(bloco).to_bytes(4, "big"))
                        f.write(bloco)
                # solta a página antes de baixar a próxima janela (senão ficam duas na memória)
                pagina = por_cc = itens = bloco = None
        except Exception as e:
            shutil.rmtree(temp, ignore_errors=True)
            self._falhas[url_global] = e
            raise
        os.replace(temp, destino)  # só vira "pronta" se a busca terminou inteira
        self._prontas.add(url_global)

    def paginas_do_cc(self, url: str) -> Iterator[list]:
        url_global, cc = url_sem_filtro_de_cc(url)
        if cc is None:
            yield from self._buscar(url)
            return
        self._carregar(url_global)
        arq = os.path.join(self._dir(url_global), _nome_arquivo(cc))
        if not os.path.exists(arq):
            return
        with open(arq, "rb") as f:
            while True:
                tamanho = f.read(4)
                if len(tamanho) < 4:
                    break
                yield pickle.loads(zlib.decompress(f.read(int.from_bytes(tamanho, "big"))))

    def limpar(self) -> None:
        shutil.rmtree(self._pasta, ignore_errors=True)


def _nome_arquivo(cc: str) -> str:
    return re.sub(r"[^0-9A-Za-z_-]", "_", cc) + ".pkl"


_ATIVA: Optional[BuscaUnica] = None


def ativa() -> Optional[BuscaUnica]:
    return _ATIVA


@contextmanager
def busca_unica(buscar: Callable[[str], Iterable[list]]):
    """Liga a busca única durante o bloco; apaga os arquivos temporários no fim."""
    global _ATIVA
    anterior = _ATIVA
    cache = BuscaUnica(buscar)
    _ATIVA = cache
    try:
        yield cache
    finally:
        _ATIVA = anterior
        logger.info("Busca única: %s buscas globais nesta rodada.", cache.buscas_globais)
        print(f"[Sienge Sync] Busca única: {cache.buscas_globais} buscas globais nesta rodada.")
        cache.limpar()
