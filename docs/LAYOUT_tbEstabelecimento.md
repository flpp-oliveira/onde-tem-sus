# tbEstabelecimento202606.csv — layout de referência

Competência **06/2026** · **627.705** registros · 56 colunas · separador `;` · campos entre aspas · encoding **latin-1**

Fontes: `DICIONARIO_DE_DADOS.docx` (layout **LFCES004 / TB_ESTABELECIMENTO**) e `SCNES_DOMINIOS.XLS` (tabelas de domínio oficiais).  
`% preench.` e `distintos` foram medidos no arquivo real — não vêm do dicionário.  
`60+` = alta cardinalidade (contagem interrompida em 60).  
⚠ no arquivo do domínio = existem códigos no dado que não constam na tabela de domínio.

| # | Campo | Tipo | Descrição | Domínio | Arquivo do domínio | % preench. | Distintos |
|---|---|---|---|---|---|---:|---:|
| 1 | `CO_UNIDADE` | VARCHAR2(31) | Código do Estabelecimento de Saúde | — | — | 100.0% | 60+ |
| 2 | `CO_CNES` | VARCHAR2(7) | Código Nacional do Estabelecimento de Saúde | — | — | 100.0% | 60+ |
| 3 | `NU_CNPJ_MANTENEDORA` | VARCHAR2(14) | CNPJ da Mantenedora | — | — | 19.4% | 60+ |
| 4 | `TP_PFPJ` | CHAR(1) | Indica se é Pessoa Física ou Jurídica | — | — | 100.0% | 2 |
| 5 | `NIVEL_DEP` | CHAR(1) | Identificador da Situação do Estabelecimento | — | — | 100.0% | 2 |
| 6 | `NO_RAZAO_SOCIAL` | VARCHAR2(60) | Razão Social | — | — | 100.0% | 60+ |
| 7 | `NO_FANTASIA` | VARCHAR2(60) | Nome Fantasia | — | — | 100.0% | 60+ |
| 8 | `NO_LOGRADOURO` | VARCHAR2(60) | Logradouro | — | — | 100.0% | 60+ |
| 9 | `NU_ENDERECO` | VARCHAR2(10) | Número | — | — | 100.0% | 60+ |
| 10 | `NO_COMPLEMENTO` | VARCHAR2(20) | Complemento | — | — | 49.1% | 60+ |
| 11 | `NO_BAIRRO` | VARCHAR2(40) | Bairro | — | — | 100.0% | 60+ |
| 12 | `CO_CEP` | VARCHAR2(8) | Código de Endereçamento Postal | — | — | 100.0% | 60+ |
| 13 | `CO_REGIAO_SAUDE` | VARCHAR2(4) | Código da Região de Saúde | `LFCES029` | — | 39.9% | 60+ |
| 14 | `CO_MICRO_REGIAO` | VARCHAR2(6) | Código da Microregião de Saúde | — | — | 0.0% | 0 |
| 15 | `CO_DISTRITO_SANITARIO` | VARCHAR2(4) | Código do Distrito Sanitário | — | — | 7.1% | 60+ |
| 16 | `CO_DISTRITO_ADMINISTRATIVO` | VARCHAR2(4) | Código do Módulo Assistencial (Conforme o plano Diretor de Regionalização do Estado/Município). | — | — | 0.2% | 60+ |
| 17 | `NU_TELEFONE` | VARCHAR2(13) | Telefone | — | — | 77.6% | 60+ |
| 18 | `NU_FAX` | VARCHAR2(13) | Fax | — | — | 0.0% | 0 |
| 19 | `NO_EMAIL` | VARCHAR2(30) | e_Mail | — | — | 57.0% | 60+ |
| 20 | `NU_CPF` | VARCHAR2(11) | CPF do Estabelecimento Esse campo só é preenchido no caso do campo PFPJ_IND = 1 | — | — | 27.0% | 60+ |
| 21 | `NU_CNPJ` | VARCHAR2(14) | CNPJ do Estabelecimento Esse campo só é preenchido no caso do campo PFPJ_IND = 3 | — | — | 54.0% | 60+ |
| 22 | `CO_ATIVIDADE` | CHAR(2) | Código da Atividade de Ensino / Pesquisa | `NFCES007` | `tbAtividadeEnsino202606.csv` | 100.0% | 5 |
| 23 | `CO_CLIENTELA` | CHAR(2) | Código de Fluxo da Clientela | `NFCES002` | `tbFluxoDadosClientela202606.csv` | 98.6% | 3 |
| 24 | `NU_ALVARA` | VARCHAR2(25) | Número do Alvará (Vigilância Sanitária) | — | — | 66.8% | 60+ |
| 25 | `DT_EXPEDICAO` | DATE | Data de Expedição do Alvará (Vigilância Sanitária) | — | — | 66.7% | 60+ |
| 26 | `TP_ORGAO_EXPEDIDOR` | CHAR(2) | Órgão Expedidor (Vigilância Sanitária) | — | — | 67.6% | 3 |
| 27 | `DT_VAL_LIC_SANI` | DATE | Data de Validade do Licenciamento Sanitário | — | — | 42.7% | 60+ |
| 28 | `TP_LIC_SANI` | VARCHAR(1) | Tipo do Licenciamento Sanitário | — | — | 42.8% | 2 |
| 29 | `TP_UNIDADE` | CHAR(2) | Tipo de Estabelecimento | TB_TIPO_UNIDADE `NFCES010` | `tbTipoUnidade202606.csv` ⚠ `16` | 100.0% | 40 |
| 30 | `CO_TURNO_ATENDIMENTO` | CHAR(2) | Código do Turno de Atendimento | `NFCES011` | `tbTurnoAtendimento202606.csv` | 99.7% | 7 |
| 31 | `CO_ESTADO_GESTOR` | CHAR(2) | Sigla do Estado | `NFCES013` | `tbEstado202606.csv` | 100.0% | 27 |
| 32 | `CO_MUNICIPIO_GESTOR` | VARCHAR2(7) | Código do Município | TB_MUNICÍPIO `NFCES005` | `tbMunicipio202606.csv` | 100.0% | 60+ |
| 33 | `TO_CHAR(DT_ATUALIZACAO,'DD/MM/YYYY')` | DATE | Data da Última Atualização do Registro | — | — | 100.0% | 60+ |
| 34 | `CO_USUARIO` | VARCHAR2(12) | Último Usuário que atualizou o Registro | — | — | 100.0% | 60+ |
| 35 | `CO_CPFDIRETORCLN` | VARCHAR2(11) | CPF do Diretor Clínico ou Gerente / Administrador | — | — | 93.2% | 60+ |
| 36 | `REG_DIRETORCLN` | VARCHAR2(60) | Registro no Conselho de Classe do Diretor Clinico | — | — | 59.8% | 60+ |
| 37 | `ST_ADESAO_FILANTROP` | CHAR(1) | Indica se o hospital fez adesão ao Programa de Reestruturação de Hospital Filantrópico | — | — | 0.3% | 2 |
| 38 | `CO_MOTIVO_DESAB` | VARCHAR2(2) | Código do Motivo de Desativação do Estabelecimento | TB_MOTIVO_DESATIVACAO `NFCES049` | `tbMotivoDesativacao202606.csv` | 21.9% | 14 |
| 39 | `NO_URL` | VARCHAR2(60) | Endereço URL | — | — | 2.0% | 60+ |
| 40 | `NU_LATITUDE` | VARCHAR2(30) | Latitude do Endereço do Estabelecimento | — | — | 90.6% | 60+ |
| 41 | `NU_LONGITUDE` | VARCHAR2(30) | Longitude do Endereço do Estabelecimento | — | — | 90.7% | 60+ |
| 42 | `TO_CHAR(DT_ATU_GEO,'DD/MM/YYYY')` | DATE | Data de atualização das Coordenadas | — | — | 78.0% | 60+ |
| 43 | `NO_USUARIO_GEO` | VARCHAR2(60) | Nome do Usuário que atualizou as Coordenadas | — | — | 77.9% | 60+ |
| 44 | `CO_NATUREZA_JUR` | VARCHAR2(04) | Código da Natureza Jurídica do Estabelecimento | TB_NATUREZA_JURIDICA `NFCES085` | `tbNaturezaJuridica202606.csv` | 100.0% | 60+ |
| 45 | `TP_ESTAB_SEMPRE_ABERTO` | CHAR(1) | Funcionamento do estabelecimento : indica se fica sempre aberto / Ininterrupto | — | — | 92.5% | 2 |
| 46 | `ST_GERACREDITO_GERENTE_SGIF` | VARCHAR(1) | Indica se o crédito gerado pelo estab. será direcionado para o Gerente/Administrador(Terceiro)/Interveniente no SGIF (Sistema de Gestão de Informações Financeiras do SUS). | — | — | 0.0% | 2 |
| 47 | `ST_CONEXAO_INTERNET` | VARCHAR(1) | Possui Conexão Internet | — | — | 94.2% | 2 |
| 48 | `CO_TIPO_UNIDADE` | CHAR(2) | Sem Uso | — | — | 0.0% | 0 |
| 49 | `NO_FANTASIA_ABREV` | VARCHAR2(21) | Sem Uso | — | — | 0.0% | 0 |
| 50 | `TP_GESTAO` | CHAR(1) | Tipo de Gestão | — | — | 100.0% | 4 |
| 51 | `TO_CHAR(DT_ATUALIZACAO_ORIGEM,'DD/MM/YYYY')` | DATE | Data da Primeira entrada no Banco de Produção Federal | — | — | 100.0% | 60+ |
| 52 | `CO_TIPO_ESTABELECIMENTO` | VARCHAR2(3) | Classificação do Estabelecimento | `NFCES119` | `tbTipoEstabelecimento202606.csv` | 93.2% | 27 |
| 53 | `CO_ATIVIDADE_PRINCIPAL` | VARCHAR2(3) | Código da Atividade Principal | `NFCES118` | — | 93.2% | 29 |
| 54 | `ST_CONTRATO_FORMALIZADO` | VARCHAR(1) | Indica se o Estabelecimento possui Contrato formalizado com o SUS | — | — | 45.6% | 2 |
| 55 | `CO_TIPO_ABRANGENCIA` | VARCHAR(02) | Código da Abrangência Telessaúde do Estabelecimento | TB_TIPO_ABRANGENCIA `NFCES125` | `tbTipoAbrangencia202606.csv` | 16.6% | 6 |
| 56 | `ST_COWORKING` | VARCHAR(1) | Indica se o estabelecimento funciona em regime de coworking | — | — | 57.8% | 2 |

## Domínios listados no próprio dicionário

Campos cujos valores válidos estão no documento, sem tabela separada:

**`TP_PFPJ`** — Indica se é Pessoa Física ou Jurídica

- 1 - Pessoa Física
- 3 - Pessoa Jurídica

**`NIVEL_DEP`** — Identificador da Situação do Estabelecimento

- 1 - Individual
- 3 - Mantido

**`TP_ORGAO_EXPEDIDOR`** — Órgão Expedidor (Vigilância Sanitária)

- 1 - SES
- 2 - SMS

**`TP_LIC_SANI`** — Tipo do Licenciamento Sanitário

- 1 - Total
- 2 - Parcial/Restrições

**`ST_ADESAO_FILANTROP`** — Indica se o hospital fez adesão ao Programa de Reestruturação de Hospital Filantrópico

- 1 - Sim
- 2 - Não

**`TP_ESTAB_SEMPRE_ABERTO`** — Funcionamento do estabelecimento : indica se fica sempre aberto / Ininterrupto

- S – SIM
- N - NÃO

**`ST_GERACREDITO_GERENTE_SGIF`** — Indica se o crédito gerado pelo estab. será direcionado para o Gerente/Administrador(Terceiro)/Interveniente no SGIF (Sistema de Gestão de Informações Financeiras do SUS).

- S – SIM
- N - NÃO

**`ST_CONEXAO_INTERNET`** — Possui Conexão Internet

- S - Sim
- N - Não

**`TP_GESTAO`** — Tipo de Gestão

- M – Municipal
- E – Estadual
- D – Dupla
- S – Sem Gestão

**`ST_CONTRATO_FORMALIZADO`** — Indica se o Estabelecimento possui Contrato formalizado com o SUS

- S - Sim
- N - Não

**`ST_COWORKING`** — Indica se o estabelecimento funciona em regime de coworking

- S – SIM
- N - NÃO

## Colunas 100% vazias no arquivo

- `CO_MICRO_REGIAO` — dicionário: *Código da Microregião de Saúde*
- `NU_FAX` — dicionário: *Fax*
- `CO_TIPO_UNIDADE` — dicionário: *Sem Uso*
- `NO_FANTASIA_ABREV` — dicionário: *Sem Uso*

## Alertas

- **`TP_UNIDADE` código `16` (257 registros): código órfão confirmado.** Não existe nem em `tbTipoUnidade202606.csv` (39 códigos) nem na aba *TIPOS DE ESTABELECIMENTO* de `SCNES_DOMINIOS.XLS`, que traz exatamente os mesmos 39 códigos. Não é defasagem do pacote de dados: o código não consta no domínio publicado pelo DATASUS. Os registros estão espalhados por 8+ UFs (RJ=77, MG=39, SP=27), foram cadastrados de 2003 em diante e **256 dos 257 estão ativos**. Por `CO_TIPO_ESTABELECIMENTO`, 207 são `016 AMBULATORIO`. Trate como *não classificado* — não descarte silenciosamente.
- `CO_MOTIVO_DESAB` preenchido = estabelecimento desativado: **137.519 de 627.705 (21.9%)**. Para trabalhar só com ativos, filtre esse campo vazio. Atenção: ~68 mil dessas baixas são administrativas por desatualização (códigos `08` e `06`), não encerramento de atividade (`10`).
- `NU_LATITUDE`/`NU_LONGITUDE` ausentes em ~9.4% dos registros.
- `CO_TIPO_UNIDADE` e `NO_FANTASIA_ABREV` são marcadas **"Sem Uso"** no dicionário e estão 100% vazias.
- `CO_REGIAO_SAUDE` e `CO_DISTRITO_SANITARIO` não têm domínio global. A aba *MAPEAMENTO TERRITORIAL* só define os **tipos** de recorte (1=Região, 2=Microrregião, 3=Módulo assistencial, 6=Distrito); os códigos são definidos por município, então só fazem sentido junto de `CO_MUNICIPIO_GESTOR`.
- `CO_ATIVIDADE_PRINCIPAL` (`NFCES118`, 29 códigos `000`–`028`): sem domínio correspondente nem na pasta de dados nem em `SCNES_DOMINIOS.XLS`. Permanece não decodificável.