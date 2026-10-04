# -*- coding: utf-8 -*-
"""A regra de nome próprio do projeto, num lugar só.

Vale para nome que a fonte entrega em CAIXA ALTA e, quase sempre, SEM ACENTO:
regiões e macrorregiões de saúde do Ministério ("SAO JOSE DO RIO PRETO",
"MADEIRA-MAMORE", "4ª RS LITORAL LESTE/JAGUARIBE"). Nome de município não
passa por aqui: o IBGE já entrega a grafia oficial ("Ji-Paraná", "Herval
d'Oeste"), e qualquer regra só a estragaria.

    >>> r = Regra(["São José do Rio Preto", "Mamoré", "Jaguaribe", "São João del Rei"])
    >>> r("SAO JOSE DO RIO PRETO")
    'São José do Rio Preto'
    >>> r("MADEIRA-MAMORE")
    'Madeira-Mamoré'
    >>> r("4ª RS LITORAL LESTE/JAGUARIBE")
    '4ª RS Litoral Leste/Jaguaribe'
    >>> r("MACRORREGIAO II")
    'Macrorregião II'
    >>> r("SAO JOAO DEL REI")
    'São João del Rei'
    >>> r("HERVAL D'OESTE")
    "Herval d'Oeste"

O que a regra faz, palavra por palavra:
- espaço, "/", "-", "(", ")", "," e "." separam palavras: o que vem depois de
  cada um começa em maiúscula ("Belo Horizonte/Nova Lima", "S.Francisco");
- de, da, do, das, dos, del, e, em, a, o, no, na ficam em minúscula, menos
  na primeira palavra ("São João del Rei", como o IBGE grafa);
- "d'" com apóstrofo fica minúsculo e a palavra seguinte começa em maiúscula
  ("Herval d'Oeste");
- siglas (RS, NRS, DRS, RRAS12, AC...) e algarismos romanos (II, III, XI)
  ficam em maiúscula, e os ordinais ("2ª") ficam como estão;
- o acento vem dos nomes de município do IBGE: "SAO" vira "São" porque é
  assim que ele aparece em "São Paulo". Só vale a palavra que o IBGE grafa de
  UM jeito: "PARANA" tem "Paraná" e "Paranã", e fica sem acento em vez de
  adivinhado. As palavras comuns que não são nome de cidade (Região, Médio,
  Área...) estão em ACENTOS_COMUNS, abaixo.
"""
import re
import unicodedata

MINUSCULAS = {"de", "da", "do", "das", "dos", "del", "e", "em", "a", "o", "no", "na"}

# Siglas que aparecem nos nomes das regiões: UF, núcleos e diretorias
# regionais de saúde (NRS, NBS, DRS, RS), a região do ABC paulista.
SIGLAS = {"AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS",
          "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC",
          "SE", "SP", "TO", "NRS", "NBS", "DRS", "CRS", "ABC", "SUS"}
ROMANO = re.compile(r"^(?=[IVXL]+$)L?X{0,3}(IX|IV|V?I{0,3})$")
SIGLA_NUM = re.compile(r"^[A-Z]+\d+$")          # RRAS12
ORDINAL = re.compile(r"^\d+[ªº°]?$")

# Palavras comuns dos nomes de região que não aparecem em nome de município,
# e por isso o IBGE não ensina o acento. E "Luís", que o IBGE grafa de dois
# jeitos (Luís e Luis): nas regiões só aparece em São Luís. Se a tabela um dia
# trouxer "LUIS CORREIA" (sem acento no IBGE), esta entrada tem de sair.
ACENTOS_COMUNS = {
    "ACO": "aço", "AQUIFERO": "aquífero", "AREA": "área", "ARIDO": "árido",
    "ATLANTICA": "atlântica", "CANTAO": "cantão", "CARBONIFERA": "carbonífera",
    "CONSORCIOS": "consórcios", "HISTORICO": "histórico", "KARAJA": "karajá",
    "LITORANEA": "litorânea", "LUIS": "luís", "MACRORREGIAO": "macrorregião",
    "MARAJO": "marajó", "MEDIO": "médio", "PLANICIE": "planície",
    "PRODUCAO": "produção", "REGIAO": "região", "SOLIMOES": "solimões",
    "TAPAJOS": "tapajós", "TRIANGULO": "triângulo", "UNICA": "única",
}

_SEPARA = re.compile(r"([\s/\-(),.]+)")


def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


class Regra:
    """Monta o dicionário de acentos a partir dos nomes do IBGE uma vez, e
    depois aplica a regra a cada nome."""

    def __init__(self, nomes_ibge):
        grafias = {}
        for n in nomes_ibge:
            for w in re.findall(r"[^\s/\-()'’.,]+", n):
                grafias.setdefault(sem_acento(w).upper(), set()).add(w.lower())
        self.acentos = {k: next(iter(v)) for k, v in grafias.items() if len(v) == 1}
        self.acentos.update(ACENTOS_COMUNS)

    def palavra(self, w, primeira):
        # "D'OESTE": o d' fica minúsculo e o resto segue a regra
        if len(w) > 2 and w[0] in "dD" and w[1] in "'’":
            return "d" + w[1] + self.palavra(w[2:], False)
        u = sem_acento(w).upper()
        if u in SIGLAS or ROMANO.match(u) or SIGLA_NUM.match(u):
            return u
        if ORDINAL.match(w):
            return w
        b = w.lower()
        if not primeira and b in MINUSCULAS:
            return b
        b = self.acentos.get(u, b)
        return b[:1].upper() + b[1:]

    def __call__(self, s):
        partes = _SEPARA.split(s.strip())
        out, primeira = [], True
        for p in partes:
            if not p or _SEPARA.fullmatch(p):
                out.append(p)
                continue
            out.append(self.palavra(p, primeira))
            primeira = False
        return "".join(out)


if __name__ == "__main__":
    import doctest
    print("doctest:", doctest.testmod())
