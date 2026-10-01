# -*- coding: utf-8 -*-
"""Prepara os dados da prova de conceito com MapLibre.

Lê dados_tratados.json, que o trata_cnes.py escreve, e monta os arquivos que
o mapa busca: os campos empacotados dos estabelecimentos, os polígonos das
UFs como GeoJSON e os municípios como pontos com patamar.

    python gera_site.py
"""
import gzip
import json
import os
import sys

sys.stdout.reconfigure(line_buffering=True, encoding="utf-8")

RAIZ = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(RAIZ, "web")
SAIDA = WEB
FONTE = os.path.join(RAIZ, "dados_tratados.json")

J = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":"))

# "SAO PAULO" -> "São Paulo", mas "PATOS DE MINAS" -> "Patos de Minas". O
# .title() do Python não conhece preposição e escrevia "Patos De Minas".
MINUSCULAS = {"de", "da", "do", "das", "dos", "e", "a", "o", "em", "no", "na"}


def titulo(s):
    partes = s.split()
    out = []
    for i, w in enumerate(partes):
        b = w.lower()
        out.append(b if i and b in MINUSCULAS else b[:1].upper() + b[1:])
    return " ".join(out)


def grava(nome, obj):
    cam = os.path.join(SAIDA, nome)
    txt = obj if isinstance(obj, str) else J(obj)
    open(cam, "w", encoding="utf-8").write(txt)
    b = txt.encode("utf-8")
    print("  %-22s %8.1f KB cru  %7.1f KB gzip"
          % (nome, len(b) / 1024, len(gzip.compress(b, 6)) / 1024))
    return len(b), len(gzip.compress(b, 6))


def descompacta(s):
    """delta + base36, o mesmo formato que o mapa usa."""
    out, a = [], 0
    for p in s.split(","):
        a += int(p, 36)
        out.append(a / 1e5)
    return out


def _dentro(p, anel):
    x, y = p
    d = False
    j = len(anel) - 1
    for i in range(len(anel)):
        xi, yi = anel[i][0], anel[i][1]
        xj, yj = anel[j][0], anel[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            d = not d
        j = i
    return d


def _area(anel):
    s = 0.0
    j = len(anel) - 1
    for i in range(len(anel)):
        s += (anel[j][0] - anel[i][0]) * (anel[j][1] + anel[i][1])
        j = i
    return abs(s) / 2


def separa_aneis(aneis):
    """Cada anel vira buraco de quem o contém, ou um polígono novo.

    Do maior para o menor, para que o continente seja examinado antes das
    ilhas e um buraco de ilha caia na ilha certa.
    """
    polis = []
    for anel in sorted(aneis, key=_area, reverse=True):
        alvo = next((p for p in polis if _dentro(anel[0], p[0])), None)
        if alvo is None:
            polis.append([anel])
        else:
            alvo.append(anel)
    return polis


def main():
    os.makedirs(SAIDA, exist_ok=True)
    if not os.path.exists(FONTE):
        sys.exit("falta dados_tratados.json — rode antes: python trata_cnes.py")
    print("lendo %s" % os.path.relpath(FONTE, RAIZ))
    D = json.load(open(FONTE, encoding="utf-8"))
    print("  %d estabelecimentos · %d municípios · %d UFs"
          % (len(D["esfera"]), len(D["muns"]), len(D["ufs"])))
    print()

    cru = gz = 0

    # --- estabelecimentos: exatamente os campos empacotados que já existem ---
    print("estabelecimentos")
    # Tudo o que a ficha do estabelecimento mostra, nos mesmos vetores
    # empacotados do site: índice no catálogo, não texto repetido.
    a, b = grava("estab.json", {"lat": D["lat"], "lon": D["lon"],
                                "esfera": D["esfera"], "mun": D["mun"],
                                "tipo": D["tipo"], "turno": D["turno"],
                                "bairro": D["bairro"], "serv": D["serv"],
                                "leitos": D["leitos"]})
    cru += a; gz += b

    # --- UFs como GeoJSON ---------------------------------------------------
    print()
    print("unidades da federação")
    feats = []
    for f in D["malha"]:
        sg = f["uf"]
        # Anéis vêm em [lon, lat], como o GeoJSON pede. O que NÃO dá para supor
        # é que os anéis depois do primeiro sejam buracos: na malha do IBGE a
        # maioria é ilha. Medido: em dez estados, 100% dos anéis extras caem
        # FORA do anel externo — 16 no Pará, 25 no Maranhão, 14 no Rio.
        #
        # Declarados como buraco, o desenhador tenta furar o polígono num lugar
        # que está fora dele, e o resultado é uma mancha triangular atravessando
        # o estado. Era isso que cortava Belém.
        polis = separa_aneis(f["a"])
        g = ({"type": "Polygon", "coordinates": polis[0]} if len(polis) == 1
             else {"type": "MultiPolygon", "coordinates": polis})
        feats.append({"type": "Feature",
                      "properties": {"uf": sg, "i": D["ufs"].index(sg)},
                      "geometry": g})
    a, b = grava("ufs.geojson", {"type": "FeatureCollection", "features": feats})
    cru += a; gz += b

    # --- municípios como pontos, com patamar --------------------------------
    print()
    print("municípios")
    lat = descompacta(D["lat"])
    lon = descompacta(D["lon"])
    mun = [int(x) for x in D["mun"].split(",")]
    esf = D["esfera"]

    # Quais tipos e quais serviços existem em cada município, como máscara de
    # bits: 28 tipos cabem num inteiro, 64 serviços em dois. Assim o cliente
    # soma estados com um OR e conta com popcount, sem refazer conjuntos.
    tipo = [int(x) for x in D["tipo"].split(",")]
    serv = [[int(y) for y in x.split(",")] if x else []
            for x in D["serv"].split("|")]

    porMun = {}
    for i, m in enumerate(mun):
        g = porMun.get(m)
        if g is None:
            g = porMun[m] = {"la": [], "lo": [], "n": 0, "pub": 0,
                             "tm": 0, "sa": 0, "sb": 0}
        g["la"].append(lat[i]); g["lo"].append(lon[i])
        g["n"] += 1
        if esf[i] == 0:
            g["pub"] += 1
        g["tm"] |= 1 << tipo[i]
        for sv in serv[i]:
            if sv < 32:
                g["sa"] |= 1 << sv
            else:
                g["sb"] |= 1 << (sv - 32)

    feats = []
    sem = 0
    for i, nome in enumerate(D["muns"]):
        g = porMun.get(i)
        if not g:
            sem += 1
            continue
        g["la"].sort(); g["lo"].sort()
        k = len(g["la"]) // 2
        feats.append({
            "type": "Feature",
            # "m" é o índice na lista completa de municípios, o mesmo que o
            # estabelecimento guarda: é por ele que a ficha volta para a cidade
            "properties": {"m": i, "nome": titulo(nome), "uf": D["ufs"][D["munUF"][i]],
                           "p": int(D["rotP"][i]) or 4,
                           "n": g["n"], "pub": g["pub"],
                           "tm": g["tm"], "sa": g["sa"], "sb": g["sb"]},
            # mediana das coordenadas dos estabelecimentos = a sede
            "geometry": {"type": "Point",
                         "coordinates": [round(g["lo"][k], 5), round(g["la"][k], 5)]},
        })
    print("  %d com sede · %d sem estabelecimento" % (len(feats), sem))
    print("  catálogo: %d tipos · %d serviços" % (len(D["tipos"]), len(D["servicos"])))
    a, b = grava("municipios.geojson", {"type": "FeatureCollection", "features": feats})
    cru += a; gz += b

    print()
    print("catálogo")
    # muns e munUF entram porque o índice `mun` do estabelecimento aponta para
    # a lista inteira de municípios, e não só para os que têm sede no mapa
    a, b = grava("catalogo.json", {"tipos": D["tipos"], "servicos": D["servicos"],
                                   "ufs": D["ufs"], "turnos": D["turnos"],
                                   "bairros": D["bairros"], "muns": D["muns"],
                                   "munUF": D["munUF"]})
    cru += a; gz += b

    print()
    print("total do mapa: %.1f KB cru · %.1f KB com gzip" % (cru / 1024, gz / 1024))
    print("  (a ficha, de 9 MB, é buscada só quando alguém abre um estabelecimento)")


if __name__ == "__main__":
    main()
