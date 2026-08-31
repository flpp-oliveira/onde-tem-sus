# Onde Tem SUS

Mapa interativo dos estabelecimentos de saúde ativos com convênio SUS no
território nacional, construído a partir da base do Cadastro Nacional de
Estabelecimentos de Saúde (CNES/DATASUS), competência 06/2026.

**108.553 estabelecimentos** — 81.756 da administração pública e 26.797
privados conveniados, em 28 tipos de unidade, 5.570 municípios e 27 UFs.

O mapa roda inteiramente no navegador: o desenho, os filtros e a busca não
dependem de servidor. A única parte com back-end é o envio de correções de
localização pela população, descrita adiante.

Artefato de trabalho de conclusão de curso.

---

## O que há aqui

| Caminho | O que é |
|---|---|
| `gera_mapa.py` | o pipeline: lê o CNES bruto e produz o site |
| `template.html` | a interface; os dados são injetados na geração |
| `web/` | o site pronto — `index.html` e `fichas.json` |
| `auditoria_bairros_202606.csv` | as 443 grafias de bairro alteradas, uma por linha |
| `functions/api/report.js` | a API que recebe as correções enviadas pela população |
| `schema.sql` | a tabela onde as correções são gravadas |
| `wrangler.toml` | configuração do Cloudflare Pages |
| `insumos/municipios_ibge.json` | código IBGE, nome e UF dos 5.570 municípios |
| `insumos/malha_uf_maxima.json` | malha das UFs, do IBGE |
| `insumos/simplifica.py` | simplificação Douglas-Peucker aplicada à malha |
| `docs/FICHA_DE_CITACAO.md` | fonte, competência e volumetria da base |
| `docs/HASHES_BASE_202606.txt` | SHA-256 dos 109 arquivos da competência |
| `docs/LAYOUT_tbEstabelecimento.md` | as 56 colunas da tabela principal do CNES |

A base bruta **não está versionada**: são 2,82 GB, e sete dos arquivos passam do
limite de 100 MB por arquivo do GitHub. Veja *Reprodução* abaixo.

---

## Correção de localização pela população

Cada ficha do mapa traz um botão **Reportar localização**. Quem conhece o local
pode indicar que o endereço está errado, que o estabelecimento não existe mais
ali ou que está duplicado — e, no caso de endereço errado, informar o endereço
certo por escrito **ou** marcar o ponto correto tocando no mapa. É possível
anexar uma foto ou print como evidência, até 5 MB.

Os envios ficam **registrados para conferência**, sem aplicação automática sobre
os dados do CNES: nenhuma correção entra no mapa sozinha.

Cada report é gravado numa tabela D1 (SQLite) e a evidência, quando existe, num
bucket R2. Para conter abuso, o IP é guardado apenas como hash SHA-256, usado só
para limitar a cinco envios por IP a cada dez minutos.

---

## Reprodução

Baixe a base da competência em
<https://cnes.datasus.gov.br/pages/downloads/arquivosBaseDeDados.jsp>,
descompacte na raiz deste repositório como `BASE_DE_DADOS_CNES_202606/`,
confira os hashes contra `docs/HASHES_BASE_202606.txt` e rode:

```
python gera_mapa.py 202606
```

Sai `web/index.html` e `web/fichas.json` — o site publicável — mais
`auditoria_bairros_202606.csv` e a base tratada. Esta última não é versionada:
são 46 MB regeneráveis a qualquer momento por este mesmo comando.

Não estão aqui os dois documentos do Ministério da Saúde consultados para
interpretar a base: guardá-los seria redistribuir obra de terceiro. A origem, a
data de acesso e o SHA-256 de cada um estão em `docs/FICHA_DE_CITACAO.md` — o
hash identifica a versão consultada mesmo sem o arquivo.

---

## Publicação

O site é servido pelo Cloudflare Pages a partir de `web/`, com a função em
`functions/api/report.js`. Antes do primeiro deploy é preciso criar o banco e o
bucket e preencher o `database_id` no `wrangler.toml`:

```
wrangler d1 create mapa-sus-reports
wrangler r2 bucket create mapa-sus-evidencias
wrangler d1 execute mapa-sus-reports --file=schema.sql --remote
```

Para rodar tudo localmente, com banco e bucket falsos nesta máquina:

```
wrangler d1 execute mapa-sus-reports --local --file=schema.sql
wrangler pages dev
```

---

## Fonte

Cadastro Nacional de Estabelecimentos de Saúde (CNES), DATASUS/Ministério da
Saúde, competência 06/2026. Malha territorial e códigos de município: IBGE.
Carta de fundo: OpenStreetMap.
