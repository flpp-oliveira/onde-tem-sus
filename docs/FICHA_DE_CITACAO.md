# Ficha de citação — base de dados do TCC

> Documento de apoio metodológico. Todos os números abaixo foram medidos nos arquivos
> em disco, não copiados de documentação. Guarde este arquivo junto da base.

## Identificação da fonte

| Item | Valor |
|---|---|
| Produtor | Ministério da Saúde (BR) — DATASUS / SCNES |
| Base | CNES — Cadastro Nacional de Estabelecimentos de Saúde |
| **Competência** | **202606 (junho de 2026)** |
| Tipo de recorte | Competência mensal fechada (não é extrato diário) |
| Página de origem | https://cnes.datasus.gov.br/pages/downloads/arquivosBaseDados.jsp |
| Data de download | **31/07/2026** |
| Pasta | `BASE_DE_DADOS_CNES_202606` |
| Conteúdo | 109 arquivos CSV · 3.029.016.056 bytes (~2,82 GiB) |

**A competência é o elemento que identifica os dados.** Sem ela, a citação aponta para
"o CNES" genérico e não permite reproduzir número nenhum. Declare `202606` no texto,
nas legendas de tabelas e gráficos e no rodapé do mapa.

## Datas internas dos dados

| Campo | Intervalo observado |
|---|---|
| `DT_ATUALIZACAO` (última atualização do registro) | 04/01/1980 a 18/04/2027 |
| `DT_ATUALIZACAO_ORIGEM` (1ª entrada no banco federal) | 30/10/2001 a **12/07/2026** |

A data mais recente de entrada no banco federal é **12/07/2026** — é o melhor indicador
de até quando a base está atualizada.

**Anomalias de data (declarar em nota de rodapé):** 1 registro com `DT_ATUALIZACAO` em
2027 (data futura, impossível) e 2 registros anteriores a 1990. Sobre 627.705 registros
é irrelevante estatisticamente, mas registrar demonstra inspeção da base.

Distribuição por ano de atualização (recentes): 2022=48.496 · 2023=28.910 · 2024=57.129 ·
2025=201.179 · 2026=157.905.

## Volumetria (para o capítulo de metodologia)

| Universo | Registros |
|---|---:|
| Estabelecimentos na competência | 627.705 |
| Ativos (`CO_MOTIVO_DESAB` vazio) | 490.186 |
| Desativados | 137.519 (21,9%) |
| Ativos com coordenada geográfica | 490.186 (**100%**) |
| Rede SUS ativa (`CO_CONVENIO = '01'`, antes dos demais filtros) | 152.382 |
| — com coordenada válida no território | 130.008 |
| — descartados por não serem assistenciais (D-23) | 21.459 |
| **Universo do mapa (recorte assistencial)** | **108.553** |
| — dos quais de natureza jurídica pública | 81.756 |
| — dos quais privados/filantrópicos conveniados | 26.797 |

## Critério de "rede SUS" adotado

Estabelecimento com **convênio SUS** (`CO_CONVENIO = '01'`) na tabela
`rlEstabAtendPrestConv202606.csv`, restrito aos ativos.

Justificativa metodológica:
- Abrange todos os tipos de atendimento (internação, ambulatorial, SADT, urgência,
  vigilância, regulação), não apenas o ambulatorial.
- Inclui a rede contratada (santas casas, filantrópicos, clínicas conveniadas): são
  27.417 estabelecimentos que atendem o cidadão pelo SUS e seriam perdidos por um
  critério de natureza jurídica.
- É regra única e objetiva, sem julgamento subjetivo — reproduzível por terceiros.

Critérios descartados e por quê:
- `TP_GESTAO` — não discrimina: 100% dos ativos são M, E ou D (nenhum "S").
- `ST_CONTRATO_FORMALIZADO` — preenchido em apenas 45,6% dos registros.
- `CO_AMBULATORIAL_SUS` (do extrato do portal) — cobre só o ambulatorial;
  retorna 104.417 contra os **152.382 com convênio SUS declarado** (medida
  tomada antes dos filtros de ativo, coordenada e recorte assistencial),
  perdendo ~48 mil.

## Verificação de integridade

SHA-256 dos **109 arquivos** da competência em `HASHES_BASE_202606.txt`, no formato
`hash  bytes  arquivo`. Calculados em 08/08/2026, antes de os brutos serem movidos
para armazenamento externo.

Os das tabelas efetivamente lidas pelo pipeline:

```
2e1f53d3c4b76f1860ab538be8c2627d3dee89cf6f34335d4938e11eb578b6a0  296623845  tbEstabelecimento202606.csv
dd606bb156c53631d0f83463f79c51065cfe9c29f8aa3bdb9f50f55020f794b6   56729650  rlEstabAtendPrestConv202606.csv
cb0802e317a9d6b9433c08be1304d2fd56abf3dd8caca6eab5307d9c2a638846  134671847  rlEstabServClass202606.csv
5b46f1bb9fdf89e076def64ea5efcdb9d3c39a4fcf9ad7f99e74afa21f8e417c    4630377  rlEstabComplementar202606.csv
cc10ddbfbb96c3cc9ab6763e5d6cd4c1ddc1af3c133ef073629c8f00d124d05f     408686  tbMunicipio202606.csv
7bf4788743760ba744454e2ee1dbfeabcb8ecb379f300e5a927a6b47e46673f9       1523  tbTipoUnidade202606.csv
```

**Para que servem.** O DATASUS reprocessa competência: um cadastro é corrigido, o
arquivo de 06/2026 é republicado, e quem baixar depois obtém conteúdo diferente com o
mesmo nome e a mesma competência. O hash é o que permite detectar essa divergência e
demonstrar qual versão sustentou os números deste trabalho.

**Onde ficam os brutos.** Fora do repositório, por limite de tamanho (2,82 GiB contra
o teto de 100 MB por arquivo do GitHub). O repositório carrega a base já tratada, o
código que a produz e estes hashes. A recuperação do bruto se faz pela fonte oficial,
na competência declarada — não por link de armazenamento pessoal, que não é citável.

Os 109 CSVs foram reunidos em `BASE_DE_DADOS_CNES_202606.zip` (696 MB, deflate),
com uma cópia desta lista de hashes dentro. O arquivo compactado tem fingerprint
própria, que a lista interna não pode cobrir:

```
89e080b7f8587a08c881f6f013c211f1be7e66fef3d00b934c91ab633b2492f7  729865739  BASE_DE_DADOS_CNES_202606.zip
```

Verificado em 08/08/2026: teste de integridade do ZIP sem erro, e o SHA-256 do
`tbEstabelecimento202606.csv` extraído do pacote confere com o da tabela acima —
a compactação é reversível sem perda.

## Documentação oficial consultada

Ambos publicados pelo Ministério da Saúde em
<https://cnes.datasus.gov.br/pages/downloads/documentacao.jsp>, acesso em
31/07/2026. O layout usado é o **LFCES004 / TB_ESTABELECIMENTO**.

| Documento | Arquivo | Uso |
|---|---|---|
| Dicionário de Dados do SCNES | `DICIONARIO_DE_DADOS.docx` | interpretação das 56 colunas → `LAYOUT_tbEstabelecimento.md` |
| Tabelas de Domínio | `SCNES_DOMINIOS.XLS` | validação dos códigos de tipo, turno e serviço |

```
086bfcbdbf47ea13d89542a21128c691367c0560a9f6bf8a2319e8a6eadb973b   611303  DICIONARIO_DE_DADOS.docx
ae3f678f1f2307d759412c735f79bf1ace5a91410261f4050dc6e86c671c2af4  1339918  SCNES_DOMINIOS.XLS
```

**Não estão no repositório**, por decisão de mantê-lo apto a uma eventual
abertura: guardá-los seria redistribuir obra de terceiro. Os hashes acima
identificam a versão consultada — se o Ministério republicar os documentos, a
divergência fica detectável.

Nenhum número deste trabalho sai dessas fontes; elas são documentação de apoio
para leitura da base, não insumo de análise.

## Fontes de validação (papel secundário)

| Fonte | Uso | Limitação |
|---|---|---|
| API DEMAS/MS — `apidadosabertos.saude.gov.br/cnes/estabelecimentos` | conferência pontual | teto de **20 registros/requisição**; sem autenticação; WAF ativo |
| Portal de dados abertos — `dadosabertos.saude.gov.br` | conferência de campos derivados | extrato **diário**, sobrescrito; não reproduzível |

Ambas acessadas em 31/07/2026. Comparação realizada com o extrato do portal:
629.840 registros (superconjunto: contém os 627.705 da competência + 2.135 cadastros
posteriores); das coordenadas comuns, **566.326 idênticas e 2.026 divergentes** (0,36%),
com divergência mediana de 0,407 km e 743 casos acima de 1 km.

## Elementos obrigatórios da referência

Confira a norma exigida pela sua instituição (ABNT NBR 6023 ou outra) e monte com:

1. **Autor institucional** — BRASIL. Ministério da Saúde. DATASUS.
2. **Título** — Cadastro Nacional de Estabelecimentos de Saúde (CNES).
3. **Especificação do recorte** — competência 06/2026 *(elemento indispensável)*.
4. **Local/meio** — Brasília: Ministério da Saúde, base de dados.
5. **URL** — https://cnes.datasus.gov.br/pages/downloads/arquivosBaseDados.jsp
6. **Data de acesso** — 31 jul. 2026.

Sem o item 3 a referência não identifica dados específicos e a análise deixa de ser
reproduzível.
