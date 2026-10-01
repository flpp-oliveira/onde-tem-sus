# -*- coding: utf-8 -*-
"""Casa as regiões de saúde com os municípios do mapa e escreve web/regioes.json.

O casamento é pelo código do IBGE, que o trata_cnes.py entrega em munCod — o
mesmo código que a tabela de regiões usa. Sem normalizar nome e sem passar
pela base bruta do CNES, de que este script não precisa mais.

    python gera_regioes.py
"""
import gzip
import json
import os
import sys

sys.stdout.reconfigure(line_buffering=True, encoding="utf-8")

RAIZ = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(RAIZ, "web")
SAIDA = os.path.join(WEB, "regioes.json")
DADOS = os.path.join(RAIZ, "dados_tratados.json")
FONTE = os.path.join(RAIZ, "insumos", "regiao_saude.json")

MINUSCULAS = {"de", "da", "do", "das", "dos", "e", "a", "o", "em", "no", "na"}


def titulo(s):
    out = []
    for i, w in enumerate(s.split()):
        b = w.lower()
        out.append(b if i and b in MINUSCULAS else b[:1].upper() + b[1:])
    return " ".join(out)



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
    munCod = D["munCod"]
    print("  %d municípios no mapa" % len(muns))

    # O casamento é pelo código do IBGE, que o trata_cnes.py entrega junto.
    # Antes era por nome, com uma ponte pelo tbMunicipio do CNES para traduzir
    # nome em código — e o nome é justamente o que não bate: o mapa mostra a
    # grafia do IBGE, enquanto o CNES e esta tabela usam outra, concordando
    # entre si. Eram 11 municípios perdidos por THOME contra TOME, DOS contra
    # DO, EUSEBIA contra EUZEBIA. Por número não há grafia que discorde, e de
    # quebra sai a dependência dos 2,82 GB da base bruta, que este script
    # precisava ter em disco só para fazer essa tradução.
    print("casando por código do IBGE")
    ligado, fora = {}, []
    for i, cod in enumerate(munCod):
        x = porCod.get(cod)
        if x:
            ligado[i] = x
        else:
            fora.append(muns[i] + " (" + ufs[munUF[i]] + ", " + cod + ")")
    print("  casaram %d de %d (%.1f%%) · fora %d"
          % (len(ligado), len(muns), 100 * len(ligado) / len(muns), len(fora)))
    # Quem sobra não é erro de grafia: é município que a tabela não tem. Ela
    # foi montada com 5.570, e o mapa chega a 5.571 — municípios instalados
    # depois dela não têm região cadastrada em lugar nenhum.
    for n in fora:
        print("    sem região na tabela: %s" % n)

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
