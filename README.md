# Onde Tem SUS

Mapa interativo dos estabelecimentos de saúde ativos com convênio SUS no
território nacional, construído a partir da base do Cadastro Nacional de
Estabelecimentos de Saúde (CNES/DATASUS), competência 06/2026.

**108.558 estabelecimentos** — 81.761 da administração pública e 26.797
privados conveniados, em 28 tipos de unidade, 5.570 municípios e 27 UFs.

O mapa roda inteiramente no navegador: o desenho, os filtros e a busca não
dependem de servidor. A única parte com back-end é o envio de correções de
localização pela população, descrita adiante.

Artefato de trabalho de conclusão de curso.

---

## O que há aqui

| Caminho | O que é |
|---|---|
| `trata_cnes.py` | lê o CNES bruto, trata e entrega o dado |
| `gera_site.py` | monta de `dados_tratados.json` os arquivos que o mapa busca |
| `gera_regioes.py` | casa as regiões de saúde com os municípios |
| `nomes.py` | a regra de nome próprio (maiúsculas e acentos) dos nomes de região |
| `web/` | o site pronto: `index.html`, `sobre.html` e os seis arquivos de dado |
| `auditoria_bairros_202606.csv` | as 443 grafias de bairro alteradas, uma por linha |
| `functions/api/report.js` | a API que recebe as correções enviadas pela população |
| `schema.sql` | a tabela onde as correções são gravadas |
| `wrangler.toml` | configuração do Cloudflare Pages |
| `insumos/municipios_ibge.json` | código IBGE, nome e UF dos 5.570 municípios |
| `insumos/malha_uf_maxima.json` | malha das UFs, do IBGE |
| `insumos/simplifica.py` | simplificação Douglas-Peucker aplicada à malha |
| `insumos/correcoes.csv` | pontos corrigidos a partir de reports analisados à mão |
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
anexar uma foto ou print como evidência, até 1 MB.

Os envios ficam **registrados para conferência**, sem aplicação automática sobre
os dados do CNES: nenhuma correção entra no mapa sozinha. A que procede, depois de
analisada à mão, entra por `insumos/correcoes.csv` (ver "Conferência dos reports").

Cada report é gravado numa tabela D1 (SQLite) e a evidência, quando existe, num
bucket R2. O IP não é guardado: para conter abuso fica só um código calculado
dele com uma chave secreta (HMAC com o `SEGREDO_IP`), que muda todo dia. A cada
envio, a rota apaga esse código dos reports com mais de 2 dias. Ele limita cada conexão a cinco envios a cada dez
minutos; o site inteiro aceita até 2.000 reports por dia.

---

## Reprodução

Baixe a base da competência em
<https://cnes.datasus.gov.br/pages/downloads/arquivosBaseDados.jsp>,
descompacte na raiz deste repositório como `BASE_DE_DADOS_CNES_202606/`,
confira os hashes contra `docs/HASHES_BASE_202606.txt` e rode:

```
python trata_cnes.py 202606
python gera_site.py
```

O primeiro trata a base e deixa `web/fichas.json`, `auditoria_bairros_202606.csv`,
a base tratada e `dados_tratados.json`. O segundo lê esse último e escreve os
cinco arquivos que o mapa busca ao abrir. O `regioes.json` sai de
`python gera_regioes.py`, que só precisa rodar quando a tabela de regiões mudar.

A base tratada e o `dados_tratados.json` não são versionados: somam 51 MB
regeneráveis a qualquer momento pelos comandos acima.

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
wrangler pages secret put SEGREDO_IP --project-name onde-tem-sus
```

O último pede o valor do segredo, que não fica em arquivo nenhum. Sem ele a rota
recusa os reports. O comando grava o segredo só no ambiente de produção, e ele
passa a valer no deploy seguinte. As prévias de deploy usam outro ambiente: para
testar o formulário nelas, o segredo também precisa ser criado ali (painel do
Pages, Settings → Variables and Secrets, ambiente Preview).

Para rodar tudo localmente, com banco e bucket falsos nesta máquina (o segredo
local vai num arquivo `.dev.vars`, fora do git):

```
wrangler d1 execute mapa-sus-reports --local --file=schema.sql
wrangler pages dev
```

O bucket não tem acesso público: nem endereço `r2.dev` nem domínio próprio
(conferido em 20/10/2026 com `wrangler r2 bucket dev-url get mapa-sus-evidencias`
e `wrangler r2 bucket domain list mapa-sus-evidencias`). As imagens só são vistas pelo painel da
Cloudflare ou pela linha de comando.

---

## Conferência dos reports

A conferência é feita à mão. Para listar os reports mais recentes, com o ponto
onde o pino estava (`lat`, `lon`) e a correção sugerida:

```
wrangler d1 execute mapa-sus-reports --remote --command "SELECT id, cnes, nome, tipo, texto, lat, lon, rua_correta, numero_correto, bairro_correto, lat_sugerida, lon_sugerida, evidencia_key, criado_em FROM reports ORDER BY id DESC LIMIT 50"
```

O `criado_em` está em UTC: um envio feito entre 21h e meia-noite no horário de
Brasília aparece com o dia seguinte. Para achar o report de um pedido de
remoção, busque pelo código CNES do estabelecimento e confira o dia com essa
diferença:

```
wrangler d1 execute mapa-sus-reports --remote --command "SELECT id, nome, tipo, texto, evidencia_key, criado_em FROM reports WHERE cnes = '<cnes>' ORDER BY id DESC"
```

Para baixar uma imagem e conferir, use no arquivo a mesma extensão da chave
(`.jpg`, `.png` ou `.webp`):

```
wrangler r2 object get mapa-sus-evidencias/<evidencia_key> --remote --file evidencia.jpg
```

Se o report procede, a correção vai para `insumos/correcoes.csv`, uma linha por
estabelecimento, com o ponto que o site passa a usar:

```
cnes;lat;lon;data;motivo
9058516;-1.29436;-47.94319;2026-10-20;Ponto do CNES cerca de 380 m ao sul da Rua Major Wilson...
```

O `trata_cnes.py` aplica as linhas depois de gravar a base tratada, que continua
sendo o CNES puro: só o que vai para o site muda. Cada correção aparece no
progresso com a distância do ponto movido. Uma linha cujo estabelecimento não
está no mapa da competência não é aplicada, e uma cujo ponto o CNES já passou a
declarar (a até 30 m) é avisada para sair do arquivo. O script para, com a linha
indicada, diante de cabeçalho errado, CNES repetido, coordenada inválida ou ponto
a mais de 50 km do declarado, que costuma ser dígito trocado.
Depois é regerar o site (`trata_cnes.py`, `gera_site.py`) e publicar. O arquivo
não leva nada de quem enviou o report: é o registro permanente da decisão.

Feita a análise, e aplicada a correção quando houver, o report é apagado, como
promete a página Sobre. Primeiro sai a imagem do bucket,
se houver, e depois a linha do banco. Nessa ordem, uma falha no meio deixa no
máximo uma linha apontando para uma imagem que já não existe, nunca uma imagem
sem linha que ninguém acharia:

```
wrangler r2 object delete mapa-sus-evidencias/<evidencia_key> --remote
wrangler d1 execute mapa-sus-reports --remote --command "DELETE FROM reports WHERE id = <id>"
```

Um pedido de remoção recebido por e-mail segue o mesmo caminho, mesmo antes da
análise.

O código de conexão (`ip_hash`) não precisa de limpeza à mão: a própria rota o
apaga dos reports com mais de 2 dias a cada envio.

---

## Fonte

Cadastro Nacional de Estabelecimentos de Saúde (CNES), DATASUS/Ministério da
Saúde, competência 06/2026. Malha territorial e códigos de município: IBGE.
Carta de fundo: OpenStreetMap.
