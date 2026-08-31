-- Banco D1 do site — só a tabela de reports de localização enviados pela
-- população. Não guarda nada além disso; o mapa em si é 100% estático.
--
-- Aplicar com:
--   wrangler d1 execute mapa-sus-reports --file=schema.sql
--   wrangler d1 execute mapa-sus-reports --file=schema.sql --remote   (produção)

CREATE TABLE IF NOT EXISTS reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  cnes TEXT NOT NULL,               -- código CNES do estabelecimento reportado
  nome TEXT,                        -- nome do estabelecimento no momento do report
                                     -- (guardado à parte: se o CNES for atualizado
                                     -- depois, o report continua legível sozinho)
  tipo TEXT NOT NULL,               -- endereco_errado | nao_existe | duplicado | outro
  texto TEXT,                       -- "detalhe do erro identificado", opcional, até 500 caracteres
  lat REAL,                         -- coordenada exibida no momento do report
  lon REAL,                         -- (referência de onde o pino estava, não sugestão de novo local)
  -- endereço correto por texto e marcação no mapa são EXCLUDENTES (um ou
  -- outro, escolhido no formulário) — nunca vêm os dois preenchidos juntos
  rua_correta TEXT,
  numero_correto TEXT,
  bairro_correto TEXT,
  lat_sugerida REAL,                -- coordenada marcada pelo usuário no mapa
  lon_sugerida REAL,
  evidencia_key TEXT,               -- chave do objeto no bucket R2, se anexou imagem
  ip_hash TEXT,                     -- hash do IP, só para limite de taxa contra abuso
  criado_em TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_reports_cnes ON reports(cnes);
CREATE INDEX IF NOT EXISTS idx_reports_criado_em ON reports(criado_em);
