# -*- coding: utf-8 -*-
"""Prova que as saídas do commit atual saem, byte a byte, da base oficial do CNES.

Confere a base bruta contra docs/HASHES_BASE_202606.txt, extrai o commit atual
(HEAD) numa pasta temporária, regera tudo lá dentro e compara cada saída com a
versão gravada no commit. Termina com código 0 só se todas forem IGUAIS.
Precisa do Python 3.12 ou mais novo (filtro de extração do tarfile).

    python verifica_reproducao.py
"""
import hashlib
import io
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time

sys.stdout.reconfigure(line_buffering=True, encoding="utf-8")
# As mensagens de erro saem pelo sys.exit, no stderr: com a mesma codificação,
# um log gravado com 2>&1 não fica com dois encodings misturados.
sys.stderr.reconfigure(encoding="utf-8")

COMP = "202606"
RAIZ = os.path.dirname(os.path.abspath(__file__))
NOME_BASE = "BASE_DE_DADOS_CNES_%s" % COMP
BASE = os.path.join(RAIZ, NOME_BASE)
HASHES = os.path.join(RAIZ, "docs", "HASHES_BASE_%s.txt" % COMP)

# As saídas versionadas do pipeline: o que o Cloudflare Pages publica e a
# auditoria de bairros. A base tratada e o dados_tratados.json não estão no
# git, então não há versão gravada com que comparar.
SAIDAS = [
    "web/estab.json",
    "web/fichas.json",
    "web/horarios.json",
    "web/catalogo.json",
    "web/municipios.geojson",
    "web/ufs.geojson",
    "web/regioes.json",
    "auditoria_bairros_%s.csv" % COMP,
]
ETAPAS = [
    ["trata_cnes.py", COMP],
    ["gera_site.py"],
    ["gera_regioes.py"],
]


def sha256(caminho):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def git(*args):
    return subprocess.run(["git", *args], cwd=RAIZ, check=True,
                          capture_output=True).stdout


def confere_base():
    """Os 109 arquivos batem com os hashes registrados na ficha de citação?"""
    esperado = {}
    for n, linha in enumerate(open(HASHES, encoding="utf-8-sig"), 1):
        if linha.strip():
            partes = linha.split(None, 2)
            if len(partes) != 3:
                sys.exit("%s, linha %d: esperado 'hash  bytes  arquivo'"
                         % (os.path.basename(HASHES), n))
            h, tam, nome = partes
            esperado[nome.strip()] = (h.lower(), int(tam))
    if not os.path.isdir(BASE):
        sys.exit("falta a base bruta em %s — veja docs/FICHA_DE_CITACAO.md" % NOME_BASE)
    presentes = sorted(os.listdir(BASE))
    sobra = set(presentes) - set(esperado)
    if sobra:
        sys.exit("arquivos na base que não estão na lista de hashes: %s" % ", ".join(sorted(sobra)))
    total = len(esperado)
    for n, (nome, (h, tam)) in enumerate(sorted(esperado.items()), 1):
        cam = os.path.join(BASE, nome)
        if not os.path.exists(cam):
            sys.exit("  falta %s na base" % nome)
        if os.path.getsize(cam) != tam or sha256(cam) != h:
            sys.exit("  %s difere do hash registrado — a base não é a da competência %s" % (nome, COMP))
        print("  %3d/%d %s (%.1f MB)" % (n, total, nome, tam / 1e6))
    return total


def liga_base(copia, total):
    """Põe a base dentro da cópia por hard link, um por arquivo.

    Não é junção nem link de pasta de propósito: apagar a pasta temporária
    remove só os links e deixa a base original intacta, enquanto uma junção
    pode ser seguida pelo rmtree e levar a base junto. Hard link exige o mesmo
    disco; se não der, o script para em vez de copiar 2,8 GB.
    """
    destino = os.path.join(copia, NOME_BASE)
    os.mkdir(destino)
    for n, nome in enumerate(sorted(os.listdir(BASE)), 1):
        try:
            os.link(os.path.join(BASE, nome), os.path.join(destino, nome))
        except OSError as e:
            sys.exit("  não foi possível ligar %s (%s) — a pasta temporária precisa "
                     "estar no mesmo disco da base" % (nome, e))
        if n % 20 == 0 or n == total:
            print("  %d/%d arquivos ligados" % (n, total))


def main():
    t0 = time.time()
    commit = git("rev-parse", "--short", "HEAD").decode().strip()
    print("commit %s · competência %s" % (commit, COMP))
    # O que se prova é o commit, não a pasta de trabalho: uma mudança ainda não
    # commitada no pipeline ou nos dados não entra na conferência.
    # quotepath=false para o git não pôr entre aspas os caminhos com acento.
    # docs/ entra porque a lista de hashes é lida da pasta de trabalho.
    status = git("-c", "core.quotepath=false", "status", "--porcelain").decode("utf-8")
    sujo = [l[3:] for l in status.splitlines()
            if l[3:].endswith(".py") or l[3:].startswith(("insumos/", "web/", "docs/"))]
    if sujo:
        print("  aviso: há mudanças não commitadas que não entram na conferência: %s"
              % ", ".join(sujo))

    print("1/6 conferindo a base bruta contra %s" % os.path.relpath(HASHES, RAIZ))
    total = confere_base()
    print("  base confere: %d arquivos" % total)

    print("2/6 lendo as saídas gravadas no commit")
    gravado = {}
    for s in SAIDAS:
        gravado[s] = hashlib.sha256(git("show", "HEAD:" + s)).hexdigest()
        print("  %s" % s)

    # A pasta fica ao lado do projeto, no mesmo disco da base, para o hard link
    # funcionar; o nome com prefixo deixa claro de onde veio, se sobrar.
    copia = tempfile.mkdtemp(prefix="verifica_reproducao_", dir=os.path.dirname(RAIZ))
    try:
        print("3/6 extraindo o commit em %s" % copia)
        tar = git("archive", "--format=tar", "HEAD")
        with tarfile.open(fileobj=io.BytesIO(tar)) as t:
            t.extractall(copia, filter="data")
        print("  %d arquivos extraídos" % sum(len(f) for _, _, f in os.walk(copia)))
        # O archive traz as saídas com os bytes do commit. Sem apagá-las, um
        # passo que deixasse de escrever uma delas resultaria num IGUAL falso;
        # assim, saída não gerada vira erro.
        for s in SAIDAS:
            os.remove(os.path.join(copia, s))

        print("4/6 ligando a base à cópia, sem copiar")
        liga_base(copia, total)

        print("5/6 regerando do zero na cópia")
        # O trata_cnes.py não fixa a codificação da saída; sem isto, o log
        # redirecionado misturaria cp1252 com o UTF-8 deste script.
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        for etapa in ETAPAS:
            print("  --- python %s" % " ".join(etapa))
            r = subprocess.run([sys.executable, "-u", *etapa], cwd=copia, env=env)
            if r.returncode:
                sys.exit("  %s falhou (código %d)" % (etapa[0], r.returncode))

        print("6/6 comparando com o commit")
        diferentes = 0
        for s in SAIDAS:
            cam = os.path.join(copia, s)
            if not os.path.exists(cam):
                sys.exit("  o pipeline não gerou %s" % s)
            igual = sha256(cam) == gravado[s]
            diferentes += not igual
            print("  %-9s %s" % ("IGUAL" if igual else "DIFERENTE", s))
    finally:
        # Só há hard links lá dentro, então o rmtree não alcança a base.
        shutil.rmtree(copia, ignore_errors=True)
        if os.path.exists(copia):
            print("  aviso: não foi possível apagar %s (arquivo em uso?). Pode apagar "
                  "à mão: lá só há hard links, e a base não é afetada." % copia)
        else:
            print("pasta temporária apagada")
        restantes = len(os.listdir(BASE))
        print("a base continua com %d arquivos" % restantes)
        if restantes != total:
            sys.exit("ALERTA: a base tinha %d arquivos e agora tem %d" % (total, restantes))

    print("tempo total: %.0f s" % (time.time() - t0))
    if diferentes:
        sys.exit("%d de %d saídas diferem do commit %s" % (diferentes, len(SAIDAS), commit))
    print("reproduzido: as %d saídas são idênticas byte a byte às do commit %s"
          % (len(SAIDAS), commit))


if __name__ == "__main__":
    main()
