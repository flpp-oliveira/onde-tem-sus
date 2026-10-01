# -*- coding: utf-8 -*-
"""Casa as regiões de saúde com os municípios do mapa e escreve web/regioes.json.

O casamento é por nome+UF porque o índice de município do mapa não guarda o
código do IBGE — ele vem de CO_MUNICIPIO_GESTOR no CNES, e é esse código que a
tabela de regiões usa. Os nomes são normalizados dos dois lados.

    python gera_regioes.py
"""
import gzip
import json
import os
import sys
import unicodedata
import csv

sys.stdout.reconfigure(line_buffering=True, encoding="utf-8")

RAIZ = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(RAIZ, "web")
SAIDA = os.path.join(WEB, "regioes.json")
DADOS = os.path.join(RAIZ, "dados_tratados.json")
FONTE = os.path.join(RAIZ, "insumos", "regiao_saude.json")
CNES = os.path.join(RAIZ, "BASE_DE_DADOS_CNES_202606", "tbMunicipio202606.csv")

MINUSCULAS = {"de", "da", "do", "das", "dos", "e", "a", "o", "em", "no", "na"}


def titulo(s):
    out = []
    for i, w in enumerate(s.split()):
        b = w.lower()
        out.append(b if i and b in MINUSCULAS else b[:1].upper() + b[1:])
    return " ".join(out)


def norma(s):
    s = unicodedata.normalize("NFD", s.upper())
    return "".join(c for c in s if unicodedata.category(c) != "Mn").strip()


def main():
    print("lendo insumos/regiao_saude.json")
    API = json.load(open(FONTE, encoding="utf-8"))
    porCod = {x["codigo_municipio"]: x for x in API}
    print("  %d municípios na tabela" % len(porCod))

    if not os.path.exists(DADOS):
        sys.exit("falta dados_tratados.json — rode antes: python trata_cnes.py")
    print("lendo dados_tratados.json")
    D = json.load(open(DADOS, encoding="utf-8"))
    muns, ufs, munUF = D["muns"], D["ufs"], D["munUF"]
    print("  %d municípios no mapa" % len(muns))

    print("lendo tbMunicipio para recuperar o código de cada um")
    pn = {}
    with open(CNES, encoding="latin-1") as f:
        for r in csv.DictReader(f, delimiter=";"):
            pn[(norma(r["NO_MUNICIPIO"]), r["CO_SIGLA_ESTADO"].strip())] = \
                r["CO_MUNICIPIO"].strip()

    # Segunda chave: o nome que a própria API usa, no formato "PA - BELEM".
    # O CNES e o IBGE discordam da grafia de alguns municípios — "São Tomé das
    # Letras" contra "São Thomé das Letras" —, e só a primeira chave perdia 16.
    porNomeAPI = {}
    for x in API:
        nm = x["municipio"]
        uf, _, resto = nm.partition(" - ")
        porNomeAPI[(norma(resto or nm), uf.strip())] = x

    print("casando")
    ligado, fora = {}, []
    porSegunda = 0
    for i, nm in enumerate(muns):
        uf = ufs[munUF[i]]
        c = pn.get((norma(nm), uf))
        x = porCod.get(c) if c else None
        if not x:
            x = porNomeAPI.get((norma(nm), uf))
            if x:
                porSegunda += 1
        if x:
            ligado[i] = x
        else:
            fora.append(nm)
    print("  recuperados pela segunda chave: %d" % porSegunda)
    print("  casaram %d de %d (%.1f%%) · fora %d"
          % (len(ligado), len(muns), 100 * len(ligado) / len(muns), len(fora)))
    if fora:
        print("    %s%s" % (", ".join(fora[:6]), " ..." if len(fora) > 6 else ""))

    # índices estáveis: a ordem é a do código, para o arquivo não mudar à toa
    codsR = sorted({x["codigo_regiao_saude"] for x in ligado.values()})
    codsM = sorted({x["codigo_macrorregiao_saude"] for x in ligado.values()})
    iR = {c: k for k, c in enumerate(codsR)}
    iM = {c: k for k, c in enumerate(codsM)}
    nomeR, nomeM = {}, {}
    for x in ligado.values():
        nomeR[x["codigo_regiao_saude"]] = titulo(x["regiao_saude"])
        nomeM[x["codigo_macrorregiao_saude"]] = titulo(x["macrorregiao_saude"])

    # -1 para o município sem região: a interface some com a linha, em vez de
    # mostrar um recorte que não existe
    colR = [iR[ligado[i]["codigo_regiao_saude"]] if i in ligado else -1
            for i in range(len(muns))]
    colM = [iM[ligado[i]["codigo_macrorregiao_saude"]] if i in ligado else -1
            for i in range(len(muns))]

    obj = {"competencia": "API Dados Abertos do SUS",
           "regioes": [nomeR[c] for c in codsR],
           "macros": [nomeM[c] for c in codsM],
           "munRegiao": ",".join(str(v) for v in colR),
           "munMacro": ",".join(str(v) for v in colM)}
    txt = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    open(SAIDA, "w", encoding="utf-8").write(txt)
    b = txt.encode("utf-8")
    print()
    print("gravado web/regioes.json  %.1f KB cru · %.1f KB gzip"
          % (len(b) / 1024, len(gzip.compress(b, 6)) / 1024))
    print("  %d regiões · %d macrorregiões" % (len(codsR), len(codsM)))

    # conferência que dá para ler a olho
    bel = [i for i, n in enumerate(muns) if n == "Belém" and ufs[munUF[i]] == "PA"]
    if bel:
        r = colR[bel[0]]
        irmaos = [muns[i] for i in range(len(muns)) if colR[i] == r]
        print("  Belém está em %s, com %d municípios: %s"
              % (obj["regioes"][r], len(irmaos), ", ".join(sorted(irmaos))))


if __name__ == "__main__":
    main()
