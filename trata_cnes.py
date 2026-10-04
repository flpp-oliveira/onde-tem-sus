# -*- coding: utf-8 -*-
"""
Gera o mapa da rede SUS a partir da base CNES (competência parametrizável) —
variante SEM correção de coordenada.

É uma cópia de `mapa/gera_mapa.py` com uma única diferença estrutural: não
carrega nem aplica a referência posicional do CNEFE/IBGE (D-25). A coordenada
exibida é sempre a que o CNES declarou, sem nenhuma correção automática. A
correção de localização, aqui, é responsabilidade da comunidade — pelo botão
"Reportar localização" de cada ficha (ver `web/index.html` e
`functions/api/report.js`).

Motivo do arquivo separado em vez de editar `mapa/gera_mapa.py`: a decisão de
não aplicar a correção automática está pendente de conversa com a
orientadora (ver memória do projeto) — o pipeline original fica intacto e
documentado, pronto para ser reativado se a decisão for essa.

Recorte: estabelecimentos ATIVOS (CO_MOTIVO_DESAB vazio) com convênio SUS
(CO_CONVENIO = '01' em rlEstabAtendPrestConv), com coordenada válida —
idêntico ao da v1.

Este script termina no dado tratado. Quem monta o site é o gera_site.py,
que lê a saída daqui.

Uso:  python trata_cnes.py [competencia]     ex.: python trata_cnes.py 202606
Saída: base_tratada_<competencia>.csv e a auditoria de bairros, que são a
       prestação de contas do tratamento; web/fichas.json, que o site
       busca ao abrir um estabelecimento; web/horarios.json, o horário de
       atendimento por dia da semana; e dados_tratados.json, a entrada do
       gera_site.py.
"""
import csv, hashlib, json, math, os, re, sys, unicodedata, collections

AQUI = os.path.dirname(os.path.abspath(__file__))
INSUMOS = os.path.join(AQUI, "insumos")    # malha do IBGE, municípios, simplificação
sys.path.insert(0, INSUMOS)
from simplifica import simplifica

COMP = sys.argv[1] if len(sys.argv) > 1 else "202606"
TOL_MALHA_FINA  = 0.002
TOL_MALHA_GROSSA = 0.02
DATA = os.path.join(AQUI, "BASE_DE_DADOS_CNES_%s" % COMP)
P = lambda n: os.path.join(DATA, "%s%s.csv" % (n, COMP))

# Caixa de sanidade da coordenada: pega dígito trocado e sinal invertido.
# LON_MAX era -33.0, a ponta leste do continente — o que excluía Fernando
# de Noronha (longitude ~-32,4), e com ela o único hospital da ilha, as duas
# unidades de saúde da família, o ambulatório e a farmácia. -28.8 passa a
# leste do arquipélago e do Atol das Rocas, e continua rejeitando o que caiu
# no Atlântico por erro de digitação.
LAT_MIN, LAT_MAX, LON_MIN, LON_MAX = -34.0, 5.5, -74.5, -28.8

csv.field_size_limit(10 ** 7)
def ler(nome):
    with open(P(nome), encoding="latin-1", newline="") as f:
        for r in csv.DictReader(f, delimiter=";"):
            yield r

def limpa(s):
    return " ".join((s or "").replace("|", "/").replace(",", " ").split()).strip()

def num(s):
    s = (s or "").strip().replace(",", ".")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None

print("competência %s (site — sem correção de posição)" % COMP)
if not os.path.isdir(DATA):
    sys.exit("pasta não encontrada: %s" % DATA)

# ---------------------------------------------------------------- domínios ---
tipos_ds  = {r["CO_TIPO_UNIDADE"]: r["DS_TIPO_UNIDADE"] for r in ler("tbTipoUnidade")}
turnos_ds = {r["CO_TURNO_ATENDIMENTO"]: r["DS_TURNO_ATENDIMENTO"] for r in ler("tbTurnoAtendimento")}
serv_ds   = {r["CO_SERVICO_ESPECIALIZADO"]: r["DS_SERVICO_ESPECIALIZADO"] for r in ler("tbServicoEspecializado")}
uf_sigla   = {r["CO_UF"]: r["CO_SIGLA"] for r in ler("tbEstado")}
mun_nome   = {r["CO_MUNICIPIO"]: (r["NO_MUNICIPIO"], r["CO_SIGLA_ESTADO"]) for r in ler("tbMunicipio")}

# ------------------------------------------- hierarquia dos municípios ---
# Em que escala o nome de cada município aparece no mapa. A régua não é
# população nem número de estabelecimentos: é a divisão regional do IBGE, em
# que cada região imediata e intermediária é nomeada pela sua sede — o centro
# urbano que polariza as demais. É hierarquia funcional oficial, e não um
# corte inventado aqui.
#
# O número de estabelecimentos seria a régua errada por construção: é a
# própria variável que o mapa apresenta. Os lugares com mais unidades
# ganhariam nome primeiro, e o mapa passaria a confirmar a si mesmo.
#
# Medido contra o Google Maps, mesma tela e mesmo centro: no nível 6 ele
# acrescenta Uberlândia, Campinas, Juiz de Fora e Montes Claros — todas sedes
# de região intermediária; no nível 7, Patos de Minas, Araxá, Curvelo e
# Barretos — todas sedes de região imediata.
CAPITAIS = {
    "RO": "Porto Velho", "AC": "Rio Branco", "AM": "Manaus", "RR": "Boa Vista",
    "PA": "Belém", "AP": "Macapá", "TO": "Palmas", "MA": "São Luís",
    "PI": "Teresina", "CE": "Fortaleza", "RN": "Natal", "PB": "João Pessoa",
    "PE": "Recife", "AL": "Maceió", "SE": "Aracaju", "BA": "Salvador",
    "MG": "Belo Horizonte", "ES": "Vitória", "RJ": "Rio de Janeiro",
    "SP": "São Paulo", "PR": "Curitiba", "SC": "Florianópolis",
    "RS": "Porto Alegre", "MS": "Campo Grande", "MT": "Cuiabá",
    "GO": "Goiânia", "DF": "Brasília",
}
# Sete regiões cujo nome não casa com nenhum município: grafia divergente do
# IBGE, ou nome composto que o desmembramento por separador não resolve.
EXCECOES_SEDE = {
    ("ES", "cachoeiro do itapemirim"): "cachoeiro de itapemirim",
    ("CE", "itapage"): "itapaje",
    ("RN", "acu"): "assu",
    ("DF", "distrito federal"): "brasilia",
}
SEP_REGIAO = re.compile(r"\s*[-\u2010-\u2015\u00bf/]\s*")


def _chave(s):
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z ]", "", s.lower()).strip()


def _uf_de(m):
    mi = m.get("microrregiao")
    if mi: return mi["mesorregiao"]["UF"]["sigla"]
    return m["regiao-imediata"]["regiao-intermediaria"]["UF"]["sigla"]


def patamares(ibge):
    """Código de 6 dígitos -> 1 capital, 2 sede intermediária, 3 imediata, 4 demais."""
    por_nome = {(_uf_de(m), _chave(m["nome"])): m["id"] for m in ibge}

    def sede(nome, uf):
        alt = EXCECOES_SEDE.get((uf, _chave(nome)))
        if alt and (uf, alt) in por_nome:
            return por_nome[(uf, alt)]
        if (uf, _chave(nome)) in por_nome:      # nome inteiro antes de partir:
            return por_nome[(uf, _chave(nome))]  # Ji-Paraná tem hífen no nome
        for parte in SEP_REGIAO.split(nome):
            if (uf, _chave(parte)) in por_nome:
                return por_nome[(uf, _chave(parte))]
        return None

    intermediarias, imediatas, sem_sede = set(), set(), 0
    for m in ibge:
        uf = _uf_de(m)
        ri = m["regiao-imediata"]
        for nome, destino in ((ri["regiao-intermediaria"]["nome"], intermediarias),
                              (ri["nome"], imediatas)):
            s = sede(nome, uf)
            if s is None: sem_sede += 1
            else: destino.add(s)
    capitais = {por_nome[(uf, _chave(n))] for uf, n in CAPITAIS.items()
                if (uf, _chave(n)) in por_nome}
    if sem_sede or len(capitais) != 27:
        raise SystemExit("hierarquia: %d regiões sem sede, %d capitais de 27"
                         % (sem_sede, len(capitais)))
    return {str(m["id"])[:6]: (1 if m["id"] in capitais else
                               2 if m["id"] in intermediarias else
                               3 if m["id"] in imediatas else 4) for m in ibge}


mun_acento = {}
patamar_cod = {}
cam_mun = os.path.join(INSUMOS, "municipios_ibge.json")
if os.path.exists(cam_mun):
    _ibge = json.load(open(cam_mun, encoding="utf-8"))
    for m in _ibge:
        mun_acento[str(m["id"])[:6]] = m["nome"]
    print("  nomes de município acentuados (IBGE): %d" % len(mun_acento))
    patamar_cod = patamares(_ibge)
    _c = collections.Counter(patamar_cod.values())
    print("  hierarquia IBGE: %d capitais · %d sedes de região intermediária"
          " · %d de região imediata · %d demais"
          % (_c[1], _c[2], _c[3], _c[4]))

# ------------------------------------------------- critério da rede (SUS) ----
sus = {r["CO_UNIDADE"] for r in ler("rlEstabAtendPrestConv") if r["CO_CONVENIO"].strip() == "01"}
print("  com convênio SUS: %d" % len(sus))

# ------------------------------------------------------------ leitos --------
leitos = collections.defaultdict(lambda: [0, 0])
leito_obst = collections.Counter()
for r in ler("rlEstabComplementar"):
    if r["CO_UNIDADE"] not in sus:
        continue
    try:
        e, s = int(r["QT_EXIST"] or 0), int(r["QT_SUS"] or 0)
    except ValueError:
        continue
    leitos[r["CO_UNIDADE"]][0] += e
    leitos[r["CO_UNIDADE"]][1] += s
    if r["CO_TIPO_LEITO"].strip() == "4":
        leito_obst[r["CO_UNIDADE"]] += e

# ----------------------------------------------------------- serviços -------
servs = collections.defaultdict(set)
for r in ler("rlEstabServClass"):
    if r["CO_UNIDADE"] in sus:
        servs[r["CO_UNIDADE"]].add(r["CO_SERVICO"])

# ------------------------------------------------------- estabelecimentos ---
ufs, iuf = [], {}
muns, imun, mun_uf = [], {}, []
# O código do IBGE de cada município, na mesma ordem de `muns`. Ele já é a
# chave do índice aqui dentro; levá-lo adiante deixa quem monta o site casar
# o município por número em vez de por nome — e nome, entre IBGE e CNES, não
# bate sempre ("São Tomé" contra "São Thomé", "do" contra "dos Carajás").
mun_cod = []
tipos, itipo = [], {}
turnos, iturno = [], {}
servicos, iserv = [], {}
def idx(v, lista, mapa):
    if v not in mapa:
        mapa[v] = len(lista); lista.append(v)
    return mapa[v]

INTENCOES = [
    ("Consulta e posto de saúde", {"01", "02", "22"}, set()),
    ("Vacina",                    {"85"},             {"174"}),
    ("Exames e diagnóstico",      {"39"},             {"120", "121", "122", "145"}),
    ("Consulta com especialista", {"04", "36"},       set()),
    ("Urgência e emergência",     {"73", "20", "21", "05", "15", "42", "76"}, set()),
    ("Saúde mental",              {"70"},             {"115"}),
    ("Reabilitação",              set(),              {"135", "164"}),
    ("Pré-natal",                 set(),              {"112"}),
    ("Parto e maternidade",       {"61"},             set()),
    ("Atendimento em casa",       {"77"},             {"113"}),
    ("Academia da saúde",         {"74"},             set()),
    ("Farmácia",                  {"43"},             set()),
    ("Saúde indígena",            {"72"},             set()),
    ("Unidade móvel",             {"40", "32"},       set()),
]
BIT_PARTO = [n for n, _, _ in INTENCOES].index("Parto e maternidade")
def mascara(tp, servicos, obst):
    m = 0
    for k, (_, tipos, svs) in enumerate(INTENCOES):
        if tp in tipos or (svs & servicos):
            m |= 1 << k
    if obst > 0:
        m |= 1 << BIT_PARTO
    return m

NAO_ASSISTENCIAL = {
    "42", "40", "32",
    "68", "81", "76",
    "50", "84", "82",
    "75", "60",
}

pts = []
descartados = collections.Counter()
for r in ler("tbEstabelecimento"):
    if r["CO_MOTIVO_DESAB"].strip():
        descartados["desativado"] += 1; continue
    u = r["CO_UNIDADE"]
    if u not in sus:
        descartados["sem convênio SUS"] += 1; continue
    if r["TP_UNIDADE"].strip() in NAO_ASSISTENCIAL:
        descartados["não assistencial"] += 1; continue
    la, lo = num(r["NU_LATITUDE"]), num(r["NU_LONGITUDE"])
    if la is None or lo is None:
        descartados["sem coordenada"] += 1; continue
    if not (LAT_MIN <= la <= LAT_MAX and LON_MIN <= lo <= LON_MAX):
        descartados["coordenada fora do Brasil"] += 1; continue

    cm = r["CO_MUNICIPIO_GESTOR"].strip()
    nm, sg = mun_nome.get(cm, ("", uf_sigla.get(r["CO_ESTADO_GESTOR"].strip(), "")))
    nm = mun_acento.get(cm, nm)
    if cm not in imun:
        imun[cm] = len(muns); muns.append(nm or cm); mun_uf.append(idx(sg, ufs, iuf))
        mun_cod.append(cm)
    tp = r["TP_UNIDADE"].strip()
    tn = r["CO_TURNO_ATENDIMENTO"].strip()
    endereco = ", ".join(x for x in [limpa(r["NO_LOGRADOURO"]), limpa(r["NU_ENDERECO"])] if x)
    if limpa(r["NO_COMPLEMENTO"]):
        endereco += " — " + limpa(r["NO_COMPLEMENTO"])

    cnes_cod = r["CO_CNES"].strip()

    pts.append(dict(
        la=la, lo=lo,
        nome=limpa(r["NO_FANTASIA"]) or limpa(r["NO_RAZAO_SOCIAL"]),
        end=endereco, bairro=limpa(r["NO_BAIRRO"]),
        _fantasia=" ".join(r["NO_FANTASIA"].split()),
        _razao=" ".join(r["NO_RAZAO_SOCIAL"].split()),
        _logr=" ".join(r["NO_LOGRADOURO"].split()),
        _num=" ".join(r["NU_ENDERECO"].split()),
        _compl=" ".join(r["NO_COMPLEMENTO"].split()),
        _bairro_origem=" ".join(r["NO_BAIRRO"].split()),
        _tel=" ".join(r["NU_TELEFONE"].split()),
        _mun_cod=cm, _mun_cnes=(mun_nome.get(cm, ("", ""))[0] or ""),
        _uf=sg, _tp=tp, _natjur=r["CO_NATUREZA_JUR"].strip(),
        _trat="",
        _u=u,                       # CO_UNIDADE: é a chave da tabela de horários
        cep="".join(ch for ch in r["CO_CEP"] if ch.isdigit()),
        tel=limpa(r["NU_TELEFONE"]), cnes=cnes_cod,
        mun=imun[cm],
        tipo=idx(tipos_ds.get(tp, "Não classificado (código %s)" % tp), tipos, itipo),
        turno=idx(turnos_ds[tn], turnos, iturno) if tn in turnos_ds else -1,
        esfera=0 if r["CO_NATUREZA_JUR"].strip().startswith("1") else 1,
        serv=sorted(idx(serv_ds.get(s, s), servicos, iserv) for s in sorted(servs.get(u, ()))),
        leitos=leitos.get(u),
        intenc=mascara(tp, servs.get(u, set()), leito_obst.get(u, 0)),
    ))

print("  no mapa: %d" % len(pts))
for k, v in descartados.most_common():
    print("    descartado — %s: %d" % (k, v))

# ------------------------------------------------- consolidação de bairros ---
ABREV = {
    "JD": "JARDIM", "JDIM": "JARDIM", "PQ": "PARQUE", "PRQ": "PARQUE",
    "VL": "VILA", "CJ": "CONJUNTO", "CONJ": "CONJUNTO",
    "RES": "RESIDENCIAL", "RESID": "RESIDENCIAL", "LOT": "LOTEAMENTO",
    "DIST": "DISTRITO", "CID": "CIDADE", "PRES": "PRESIDENTE",
    "GOV": "GOVERNADOR", "PROF": "PROFESSOR", "STO": "SANTO", "STA": "SANTA",
}
por_mun = collections.defaultdict(set)
for p in pts:
    por_mun[p["mun"]].add(p["bairro"])

canon, fundidos = {}, 0
for m, bs in por_mun.items():
    for b in sorted(bs):
        partes = b.split()
        if partes and partes[0] in ABREV:
            alvo = " ".join([ABREV[partes[0]]] + partes[1:])
            if alvo in bs:
                canon[(m, b)] = alvo
                fundidos += 1

antes = sum(len(v) for v in por_mun.values())
auditoria = [("municipio", "grafia_original", "grafia_adotada", "freq_original",
              "freq_adotada", "regra")]
for (m, b), alvo in canon.items():
    auditoria.append((muns[m], b, alvo, "", "", "abreviatura"))
for p in pts:
    novo = canon.get((p["mun"], p["bairro"]))
    if novo:
        p["bairro"] = novo; p["_trat"] = "abreviatura"

import re as _re
NUMERAL = _re.compile(r"(\d|\b(I{1,3}|IV|V|VI{0,3}|IX|X)\b)")
def dist1(a, b):
    if abs(len(a) - len(b)) > 1:
        return False
    ant = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            cur[j] = min(ant[j] + 1, cur[j - 1] + 1, ant[j - 1] + (ca != cb))
        ant = cur
    return ant[-1] == 1

freq = collections.defaultdict(collections.Counter)
for p in pts:
    freq[p["mun"]][p["bairro"]] += 1

corrigidos, trocas = 0, {}
for m, bs in freq.items():
    nomes = sorted(bs)
    for i in range(len(nomes)):
        for j in range(i + 1, len(nomes)):
            a, b = nomes[i], nomes[j]
            if b.startswith(a + " ") or not dist1(a, b):
                continue
            dom, raro = (a, b) if bs[a] >= bs[b] else (b, a)
            if bs[raro] != 1 or bs[dom] < 5:
                continue
            if NUMERAL.search(a) or NUMERAL.search(b):
                continue
            trocas[(m, raro)] = dom
            auditoria.append((muns[m], raro, dom, 1, bs[dom], "grafia"))
            corrigidos += 1

bairros, ibairro = [], {}
for p in pts:
    novo = trocas.get((p["mun"], p["bairro"]))
    if novo:
        p["bairro"] = novo
        p["_trat"] = (p["_trat"] + "+grafia") if p["_trat"] else "grafia"
    p["ibairro"] = idx(p["bairro"], bairros, ibairro)

depois = len({(p["mun"], p["bairro"]) for p in pts})
cam_aud = os.path.join(AQUI, "auditoria_bairros_%s.csv" % COMP)
with open(cam_aud, "w", encoding="utf-8-sig", newline="") as f:
    csv.writer(f, delimiter=";").writerows(auditoria)
print("  bairros: %d -> %d pares (município, bairro)" % (antes, depois))
print("    abreviaturas consolidadas: %d | grafias corrigidas: %d" % (fundidos, corrigidos))

# ---------------------------------------------------- base tratada (CSV) -----
CAB = ["cnes", "nome_fantasia", "razao_social", "tipo_codigo", "tipo",
       "natureza_juridica_codigo", "esfera", "turno",
       "logradouro", "numero", "complemento", "cep", "telefone",
       "bairro", "bairro_origem", "bairro_tratamento",
       "municipio_codigo", "municipio", "municipio_origem", "uf",
       "latitude", "longitude",
       "leitos_sus", "qtd_servicos", "servicos"]
cam_base = os.path.join(AQUI, "base_tratada_%s.csv" % COMP)
ordem = sorted(pts, key=lambda p: (p["_uf"], muns[p["mun"]], p["cnes"]))
with open(cam_base, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    w.writerow(CAB)
    for p in ordem:
        svs = [servicos[i] for i in p["serv"]]
        w.writerow([
            p["cnes"], p["_fantasia"], p["_razao"], p["_tp"], tipos[p["tipo"]],
            p["_natjur"], "Administração pública" if p["esfera"] == 0 else "Privada conveniada",
            turnos[p["turno"]] if p["turno"] >= 0 else "",
            p["_logr"], p["_num"], p["_compl"], p["cep"], p["_tel"],
            p["bairro"], p["_bairro_origem"], p["_trat"],
            p["_mun_cod"], muns[p["mun"]], p["_mun_cnes"], p["_uf"],
            "%.5f" % p["la"], "%.5f" % p["lo"],
            p["leitos"] if p["leitos"] else "", len(svs), "; ".join(svs),
        ])
tam_base = os.path.getsize(cam_base)
_h = hashlib.sha256()
with open(cam_base, "rb") as f:
    for _b in iter(lambda: f.read(1 << 22), b""):
        _h.update(_b)
print("  base tratada: %s  %d linhas · %.1f MB" %
      (os.path.basename(cam_base), len(ordem), tam_base / 1024 ** 2))
print("    sha256: %s" % _h.hexdigest())

# ------------------------------------------------------------ serialização --
pts.sort(key=lambda p: (p["la"], p["lo"]))
def delta36(vals):
    out, ant = [], 0
    for v in vals:
        i = int(round(v * 1e5))
        out.append(_b36(i - ant))
        ant = i
    return ",".join(out)
def _b36(n):
    if n == 0: return "0"
    s, neg = "", n < 0
    n = abs(n)
    while n:
        n, d = divmod(n, 36)
        s = "0123456789abcdefghijklmnopqrstuvwxyz"[d] + s
    return ("-" + s) if neg else s

malha, malha_grossa = [], []
cam_malha = os.path.join(INSUMOS, "malha_uf_maxima.json")
if os.path.exists(cam_malha):
    geo = json.load(open(cam_malha, encoding="utf-8"))
    for f in simplifica(geo, TOL_MALHA_FINA):
        sg = uf_sigla.get(f["uf"].zfill(2), f["uf"])
        aneis = [[[round(x, 4), round(y, 4)] for x, y in a] for a in f["aneis"]]
        malha.append({"uf": sg, "a": aneis})
    for f in simplifica(geo, TOL_MALHA_GROSSA):
        malha_grossa.append({"a": [[[round(x, 4), round(y, 4)] for x, y in a]
                                   for a in f["aneis"]]})
    print("  malha de UFs: %d unidades" % len(malha))

# ------------------------------------------------- rótulos dos municípios ---
# Só o patamar viaja: um dígito por município, alinhado ao índice interno de
# `muns` — o mesmo do seletor.
#
# A ÂNCORA não vem daqui. Ela era o centroide de área do polígono, e centroide
# não é sede: Palmas tem a sede na beira do rio e o território esticado para
# leste, então o nome saía 80 km fora do lugar, contra o próprio topônimo da
# carta do OpenStreetMap por baixo. Quem sabe onde fica a cidade é o dado que
# o mapa já carrega — a MEDIANA das coordenadas dos estabelecimentos do
# município, calculada no cliente. Mediana, e não média, porque um posto
# rural isolado desloca a média e não mexe na mediana. De quebra saem 24,8 KB
# de tabela de âncoras da página.
rot_p = [0] * len(muns)
for _cod, _i in imun.items():
    rot_p[_i] = patamar_cod.get(_cod, 4)
_sem = sum(1 for v in rot_p if v == 0)
print("  patamar por município: %d classificados, %d sem"
      % (len(rot_p) - _sem, _sem))

dados = {
    "rotP": "".join(str(p) for p in rot_p),
    "malha": malha,
    "malhaGrossa": malha_grossa,
    "lat": delta36([p["la"] for p in pts]),
    "lon": delta36([p["lo"] for p in pts]),
    "nome":   "|".join(p["nome"] for p in pts),
    "end":    "|".join(p["end"] for p in pts),
    "bairro": ",".join(str(p["ibairro"]) for p in pts),
    "bairros": bairros,
    "cep":    "|".join(p["cep"] for p in pts),
    "tel":    "|".join(p["tel"] for p in pts),
    "cnes":   "|".join(p["cnes"] for p in pts),
    "tipo":  ",".join(str(p["tipo"]) for p in pts),
    "mun":   ",".join(str(p["mun"]) for p in pts),
    "turno": ",".join(str(p["turno"]) for p in pts),
    "esfera": [p["esfera"] for p in pts],
    "serv": "|".join(",".join(str(s) for s in p["serv"]) for p in pts),
    "leitos": {str(i): p["leitos"] for i, p in enumerate(pts) if p["leitos"]},
    "tipos": tipos, "turnos": turnos, "servicos": servicos,
    "muns": muns, "munCod": mun_cod, "munUF": mun_uf, "ufs": ufs,
    "competencia": COMP,
}

J = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":"))

# A ficha — nome, endereço, CEP, telefone e CNES — sai do pacote principal
# e vira arquivo próprio: o mapa só precisa dela quando alguém abre um
# estabelecimento, e são 9 MB que não devem pesar na primeira pintura.
CAMPOS_FICHA = ["nome", "end", "cep", "tel", "cnes"]
fichas = {k: dados.pop(k) for k in CAMPOS_FICHA}

web = os.path.join(AQUI, "web")
os.makedirs(web, exist_ok=True)
open(os.path.join(web, "fichas.json"), "w", encoding="utf-8").write(J(fichas))

# ---------------------------------------------------------------- horários --
# O turno ("manhã e tarde") não responde se está aberto AGORA: 79% dos
# estabelecimentos caem numa opção só. A tbEstabHorarioAtend tem dia da semana
# e faixa de hora para 90% deles. Dia: 1 é domingo e 7 é sábado — medido, o 1
# e o 7 são os dias com menos atendimento (1.657 e 9.299 estabelecimentos,
# contra ~96 mil de segunda a sexta), e o sábado tem mais que o domingo.
#
# Formato: os padrões semanais DISTINTOS numa lista, e cada estabelecimento
# aponta para o seu. São 5.339 padrões para 97 mil estabelecimentos — "de
# segunda a sexta, das 7h às 17h" sozinho cobre 20 mil. Um padrão é
# "23456:0700-1200,1400-1700": os dias, e as faixas que eles têm em comum.
#
# Duas normalizações, ambas para dizer 24 h do jeito que o site entende:
# início igual ao fim ("07:00–07:00", "00:00–00:00") é como o cadastro declara
# o plantão de um dia inteiro, e 23:59 como fim é a meia-noite.
#
# `atual` é o ano e o mês (aamm) da atualização mais recente do horário, para
# a ficha dizer de quando ele é. Data posterior à competência é erro de
# digitação do cadastro e fica de fora.
def _hm(h):
    try:
        a, b = h.split(":")
        v = int(a) * 100 + int(b)
        return v if 0 <= int(a) <= 24 and 0 <= int(b) < 60 else None
    except ValueError:
        return None

pos = {p["_u"]: k for k, p in enumerate(pts)}
faixas = collections.defaultdict(set)
atual = {}
_lidas = 0
for r in ler("tbEstabHorarioAtend"):
    _lidas += 1
    if _lidas % 1000000 == 0:
        print("  horários: %d linhas lidas" % _lidas)
    k = pos.get(r["CO_UNIDADE"])
    if k is None:
        continue
    a, b = _hm(r["HR_INICIO_ATENDIMENTO"]), _hm(r["HR_FIM_ATENDIMENTO"])
    dia = r["CO_DIA_SEMANA"].strip()
    if a is None or b is None or dia not in "1234567" or len(dia) != 1:
        continue
    if a == b:
        a, b = 0, 2400
    if b == 2359:
        b = 2400
    faixas[k].add((dia, a, b))
    d = r["TO_CHAR(DT_ATUALIZACAO,'DD/MM/YYYY')"].strip()
    if len(d) == 10 and d[6:10] + d[3:5] <= COMP:
        am = d[8:10] + d[3:5]
        if am > atual.get(k, ""):
            atual[k] = am

def _padrao(fx):
    por_dia = collections.defaultdict(list)
    for dia, a, b in sorted(fx):
        por_dia[dia].append("%04d-%04d" % (a, b))
    grupos = collections.defaultdict(list)
    for dia in sorted(por_dia):
        grupos[",".join(por_dia[dia])].append(dia)
    return ";".join("".join(ds) + ":" + f for f, ds in
                    sorted(grupos.items(), key=lambda g: g[1][0]))

padroes, ipad, cod = [], {}, []
for k in range(len(pts)):
    if k not in faixas:
        cod.append("")
        continue
    pd = _padrao(faixas[k])
    if pd not in ipad:
        ipad[pd] = len(padroes)
        padroes.append(pd)
    cod.append(str(ipad[pd]))
horarios = {"padroes": padroes, "h": ",".join(cod),
            "atual": ",".join(atual.get(k, "") for k in range(len(pts)))}
open(os.path.join(web, "horarios.json"), "w", encoding="utf-8").write(J(horarios))
print("  horários: %d de %d estabelecimentos (%.1f%%), %d padrões semanais"
      % (len(faixas), len(pts), 100 * len(faixas) / len(pts), len(padroes)))

# O resto fica num arquivo próprio, e não embutido numa página pronta.
# Enquanto o dado trafegava dentro do HTML gerado, quem montava o site
# tinha de abrir esse HTML e pescar o JSON de dentro com expressão regular:
# o site dependia de uma página que ele mesmo viria a substituir. Aqui
# termina o tratamento do CNES, e daqui o gera_site.py começa.
cam_dados = os.path.join(AQUI, "dados_tratados.json")
open(cam_dados, "w", encoding="utf-8").write(J(dados))

import gzip as _gz
gz = lambda p: len(_gz.compress(open(p, "rb").read(), 6))
n_fic = os.path.getsize(os.path.join(web, "fichas.json"))
print()
print("gerado: web/fichas.json      %5.1f MB  (%.1f MB com gzip)"
      % (n_fic / 1e6, gz(os.path.join(web, "fichas.json")) / 1e6))
n_hor = os.path.getsize(os.path.join(web, "horarios.json"))
print("gerado: web/horarios.json    %5.1f MB  (%.1f MB com gzip)"
      % (n_hor / 1e6, gz(os.path.join(web, "horarios.json")) / 1e6))
print("gerado: dados_tratados.json  %5.1f MB  (não publicado; entra no gera_site.py)"
      % (os.path.getsize(cam_dados) / 1e6,))
