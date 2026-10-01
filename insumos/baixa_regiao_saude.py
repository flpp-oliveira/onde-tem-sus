# -*- coding: utf-8 -*-
"""Baixa a tabela de regiões de saúde da API de Dados Abertos do SUS.

Cada município brasileiro pertence a uma região de saúde, definida pela
Comissão Intergestores Bipartite do estado (Decreto 7.508/2011). É o recorte em
que o SUS de fato organiza o atendimento: quase metade dos municípios não tem
hospital, e é a região que responde por eles.

O FTP do DATASUS não é alcançável de toda rede e os navegadores não abrem mais
ftp://. Esta API serve o mesmo conteúdo por HTTP e pagina por deslocamento de
itens — `offset` conta ITENS, não páginas, medido: incrementar de 1 devolve a
mesma página deslocada de uma linha.

    python insumos/baixa_regiao_saude.py
"""
import json
import os
import sys
import time
import urllib.request

sys.stdout.reconfigure(line_buffering=True, encoding="utf-8")

AQUI = os.path.dirname(os.path.abspath(__file__))
URL = ("https://apidadosabertos.saude.gov.br/macrorregiao-e-regiao-de-saude"
       "/municipio?limit=%d&offset=%d")
CHAVE = "macrorregiao_regiao_saude_municipios"
LOTE = 500
SAIDA = os.path.join(AQUI, "regiao_saude.json")


def main():
    print("baixando de apidadosabertos.saude.gov.br")
    todos, off = [], 0
    while True:
        req = urllib.request.Request(URL % (LOTE, off),
                                     headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=120) as r:
            lote = json.loads(r.read().decode("utf-8")).get(CHAVE, [])
        todos += lote
        print("  %5d linhas acumuladas" % len(todos))
        if len(lote) < LOTE:
            break
        off += LOTE
        time.sleep(0.2)
        if off > 20000:
            sys.exit("ABORTADO: paginação não terminou, algo mudou na API")

    if len(todos) < 5000:
        sys.exit("ABORTADO: só %d linhas, esperava ~5.570" % len(todos))

    txt = json.dumps(todos, ensure_ascii=False, separators=(",", ":"))
    open(SAIDA, "w", encoding="utf-8").write(txt)
    print()
    print("gravado insumos/%s  %.1f KB" % (os.path.basename(SAIDA), len(txt.encode()) / 1024))
    print("  municípios ..... %d" % len({x["codigo_municipio"] for x in todos}))
    print("  regiões ........ %d" % len({x["codigo_regiao_saude"] for x in todos}))
    print("  macrorregiões .. %d" % len({x["codigo_macrorregiao_saude"] for x in todos}))


if __name__ == "__main__":
    main()
