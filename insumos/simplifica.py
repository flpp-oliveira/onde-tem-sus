# -*- coding: utf-8 -*-
"""Simplificação Douglas-Peucker da malha de UFs do IBGE (iterativa, sem dependências)."""
import json, os, sys

AQUI = os.path.dirname(os.path.abspath(__file__))

def dp(pts, tol):
    """Douglas-Peucker iterativo. Trata anel fechado: quando a linha base degenera
    (primeiro == último ponto), mede distância ao ponto inicial, não à reta."""
    n = len(pts)
    if n < 3:
        return list(pts)
    manter = [False] * n
    manter[0] = manter[n - 1] = True
    pilha = [(0, n - 1)]
    while pilha:
        i0, i1 = pilha.pop()
        if i1 <= i0 + 1:
            continue
        x0, y0 = pts[i0]
        x1, y1 = pts[i1]
        dx, dy = x1 - x0, y1 - y0
        den = (dx * dx + dy * dy) ** 0.5
        dmax, idx = -1.0, -1
        if den < 1e-12:                      # base degenerada (anel fechado)
            for i in range(i0 + 1, i1):
                x, y = pts[i]
                d = ((x - x0) ** 2 + (y - y0) ** 2) ** 0.5
                if d > dmax:
                    dmax, idx = d, i
        else:
            c = x1 * y0 - y1 * x0
            for i in range(i0 + 1, i1):
                x, y = pts[i]
                d = abs(dy * x - dx * y + c) / den
                if d > dmax:
                    dmax, idx = d, i
        if dmax > tol and idx > 0:
            manter[idx] = True
            pilha.append((i0, idx))
            pilha.append((idx, i1))
    return [pts[i] for i in range(n) if manter[i]]

def simplifica(geo, tol, min_pts=4):
    """Aplica a todos os anéis. O piso é baixo de propósito: ilhas costeiras
    têm poucos vértices e descartá-las coloca estabelecimentos no mar."""
    saida = []
    for f in geo["features"]:
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        novos = []
        for poly in polys:
            anel = [tuple(p[:2]) for p in poly[0]]      # só o anel externo
            s = dp(anel, tol)
            if len(s) >= min_pts:
                novos.append(s)
        if novos:
            saida.append({"uf": f["properties"]["codarea"], "aneis": novos})
    return saida

def total(m):
    return sum(len(a) for f in m for a in f["aneis"])

if __name__ == "__main__":
    geo = json.load(open(os.path.join(AQUI, "malha_uf.json"), encoding="utf-8"))
    orig = sum(len(r) for f in geo["features"]
               for poly in (f["geometry"]["coordinates"]
                            if f["geometry"]["type"] == "MultiPolygon"
                            else [f["geometry"]["coordinates"]])
               for r in poly)
    print("pontos originais: %d" % orig)
    for tol in (0.002, 0.005, 0.01, 0.02, 0.05):
        m = simplifica(geo, tol)
        print("  tol %-6s -> %5d pontos · %2d UFs · ~%4.0f KB"
              % (tol, total(m), len(m), total(m) * 13 / 1000))
