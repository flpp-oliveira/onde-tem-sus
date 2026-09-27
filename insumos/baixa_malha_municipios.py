# -*- coding: utf-8 -*-
"""Baixa a malha municipal do IBGE e a grava como insumo do projeto.

Roda UMA vez, à mão. O resultado — malha_municipios_minima.json — fica
versionado ao lado de malha_uf_maxima.json, e é ele que gera_mapa.py lê. A
geração do mapa não acessa a rede: se dependesse da API do IBGE, uma
indisponibilidade do serviço quebraria a build, e duas builds da mesma
competência poderiam divergir.

Qualidade "minima" é deliberada. Medido nas 27 UFs: 3,44 MB cru contra 9,9 MB
da "intermediaria", e nas escalas em que o mapa mostra divisas municipais a
diferença de contorno não se vê. A simplificação de Douglas-Peucker ainda passa
por cima disso em gera_mapa.py.

    python insumos/baixa_malha_municipios.py
"""
import gzip
import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.stdout.reconfigure(line_buffering=True)

AQUI = os.path.dirname(os.path.abspath(__file__))
SAIDA = os.path.join(AQUI, "malha_municipios_minima.json")

# código do IBGE -> sigla, na ordem em que aparecem no mapa
UFS = [
    (11, "RO"), (12, "AC"), (13, "AM"), (14, "RR"), (15, "PA"), (16, "AP"),
    (17, "TO"), (21, "MA"), (22, "PI"), (23, "CE"), (24, "RN"), (25, "PB"),
    (26, "PE"), (27, "AL"), (28, "SE"), (29, "BA"), (31, "MG"), (32, "ES"),
    (33, "RJ"), (35, "SP"), (41, "PR"), (42, "SC"), (43, "RS"), (50, "MS"),
    (51, "MT"), (52, "GO"), (53, "DF"),
]
URL = ("https://servicodados.ibge.gov.br/api/v3/malhas/estados/%d"
       "?formato=application/vnd.geo+json&intrarregiao=municipio"
       "&qualidade=minima")


def baixa(url, tentativas=3):
    """GET com gzip e reenvio. A API do IBGE devolve 5xx esporádico."""
    for t in range(1, tentativas + 1):
        try:
            req = urllib.request.Request(url, headers={"Accept-Encoding": "gzip"})
            r = urllib.request.urlopen(req, timeout=180)
            d = r.read()
            if r.headers.get("Content-Encoding") == "gzip":
                d = gzip.decompress(d)
            return d
        except (urllib.error.URLError, TimeoutError) as e:
            if t == tentativas:
                raise
            print("      tentativa %d falhou (%s), repetindo em %ds" % (t, e, 3 * t))
            time.sleep(3 * t)


def main():
    print("malha municipal do IBGE — 27 unidades da federação")
    saida, total_mun, total_vert = {}, 0, 0
    t0 = time.time()
    for n, (cod, sigla) in enumerate(UFS, 1):
        bruto = baixa(URL % cod)
        geo = json.loads(bruto.decode("utf-8"))
        mun = []
        for f in geo["features"]:
            g = f["geometry"]
            cs = g["coordinates"]
            polys = [cs] if g["type"] == "Polygon" else cs
            aneis = [[[x, y] for x, y in anel] for poly in polys for anel in poly]
            mun.append({"cod": f["properties"]["codarea"], "aneis": aneis})
            total_vert += sum(len(a) for a in aneis)
        saida[sigla] = mun
        total_mun += len(mun)
        print("  [%2d/27] %s  %4d municípios  %7d vértices acumulados"
              % (n, sigla, len(mun), total_vert))

    with open(SAIDA, "w", encoding="utf-8") as fp:
        json.dump(saida, fp, ensure_ascii=False, separators=(",", ":"))
    mb = os.path.getsize(SAIDA) / 1e6
    print()
    print("gravado: %s" % os.path.basename(SAIDA))
    print("  %d municípios · %d vértices · %.2f MB · %.0f s"
          % (total_mun, total_vert, mb, time.time() - t0))


if __name__ == "__main__":
    main()
