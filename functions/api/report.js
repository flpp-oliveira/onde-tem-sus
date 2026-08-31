// Cloudflare Pages Function — POST /api/report
//
// Recebe o report de localização enviado pelo botão da ficha (ver
// template.html, seção "reportar localização") e grava:
//   - os campos de texto/número no banco D1 (binding "DB")
//   - a evidência em imagem, se anexada, no bucket R2 (binding "EVIDENCIAS")
//
// Deliberadamente simples: não há moderação nem aplicação automática da
// correção — o report só fica registrado para consulta manual. A decisão de
// como tratar os reports (revisão manual, limiar de repetição, etc.) é
// posterior e não faz parte deste entregável.
//
// O corpo chega como multipart/form-data (não JSON), porque pode incluir um
// arquivo — o FormData do navegador monta isso sozinho no fetch do template.

const TIPOS_VALIDOS = new Set(["endereco_errado", "nao_existe", "duplicado", "outro"]);
const LIMITE_TEXTO = 500;
const LIMITE_RUA = 120, LIMITE_NUMERO = 20, LIMITE_BAIRRO = 80;
const LIMITE_EVIDENCIA = 5 * 1024 * 1024; // 5 MB — mesmo limite validado no cliente
const JANELA_LIMITE_MINUTOS = 10;
const MAX_REPORTS_NA_JANELA = 5; // por IP, contra abuso básico

function json(dados, status = 200) {
  return new Response(JSON.stringify(dados), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  });
}

async function hashIp(ip) {
  // hash, não o IP em texto puro — suficiente para limitar taxa de envio sem
  // guardar dado pessoal identificável diretamente no banco
  const dados = new TextEncoder().encode("mapa-sus-report::" + ip);
  const buf = await crypto.subtle.digest("SHA-256", dados);
  return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, "0")).join("");
}

function numOuNull(v) {
  // campo ausente no formulario chega como null, e campo vazio como "".
  // Number() converte os dois para 0, que passaria por Number.isFinite e
  // gravaria a coordenada 0,0 (um ponto no oceano) como se fosse informada.
  if (v === null || v === undefined) return null;
  const s = String(v).trim();
  if (s === "") return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}

function extensaoDe(nomeOuTipo) {
  const m = /\.(\w+)$/.exec(nomeOuTipo || "");
  if (m) return m[1].toLowerCase();
  const porTipo = { "image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/gif": "gif" };
  return porTipo[nomeOuTipo] || "bin";
}

export async function onRequestPost(context) {
  const { request, env } = context;

  const tipoConteudo = request.headers.get("content-type") || "";
  if (!tipoConteudo.includes("multipart/form-data")) {
    return json({ erro: "content-type inválido, esperado multipart/form-data" }, 400);
  }

  let form;
  try {
    form = await request.formData();
  } catch {
    return json({ erro: "corpo inválido" }, 400);
  }

  const cnes = String(form.get("cnes") || "").trim();
  const tipo = String(form.get("tipo") || "").trim();
  const texto = String(form.get("texto") || "").trim().slice(0, LIMITE_TEXTO);
  const nome = String(form.get("nome") || "").trim().slice(0, 200);
  const ruaCorreta = String(form.get("rua_correta") || "").trim().slice(0, LIMITE_RUA);
  const numeroCorreto = String(form.get("numero_correto") || "").trim().slice(0, LIMITE_NUMERO);
  const bairroCorreto = String(form.get("bairro_correto") || "").trim().slice(0, LIMITE_BAIRRO);
  const lat = numOuNull(form.get("lat"));
  const lon = numOuNull(form.get("lon"));
  const latSug = numOuNull(form.get("lat_sugerida"));
  const lonSug = numOuNull(form.get("lon_sugerida"));

  if (!/^\d{7}$/.test(cnes)) {
    return json({ erro: "cnes inválido" }, 400);
  }
  if (!TIPOS_VALIDOS.has(tipo)) {
    return json({ erro: "tipo inválido" }, 400);
  }

  const ip = request.headers.get("CF-Connecting-IP") || "desconhecido";
  const ipHash = await hashIp(ip);

  // limite básico de taxa: sem isso, um script poderia inundar o banco/bucket
  // a janela é calculada pelo próprio SQLite: criado_em é gravado por
  // datetime('now') ("2026-08-31 13:39:51"), formato diferente do ISO do
  // JavaScript ("2026-08-31T13:39:51.000Z"). Como a comparação é textual,
  // misturar os dois faz o filtro nunca casar e o limite não valer nada.
  const { results } = await env.DB.prepare(
    `SELECT COUNT(*) AS n FROM reports
      WHERE ip_hash = ? AND criado_em >= datetime('now', ?)`
  ).bind(ipHash, `-${JANELA_LIMITE_MINUTOS} minutes`).all();
  if ((results?.[0]?.n ?? 0) >= MAX_REPORTS_NA_JANELA) {
    return json({ erro: "muitos reports em pouco tempo, tente novamente mais tarde" }, 429);
  }

  // ---- evidência (opcional) --------------------------------------------------
  let evidenciaKey = null;
  const arquivo = form.get("evidencia");
  if (arquivo && typeof arquivo === "object" && arquivo.size > 0) {
    if (!arquivo.type || !arquivo.type.startsWith("image/")) {
      return json({ erro: "evidência precisa ser uma imagem" }, 400);
    }
    if (arquivo.size > LIMITE_EVIDENCIA) {
      return json({ erro: "evidência maior que 5 MB" }, 400);
    }
    const ext = extensaoDe(arquivo.name || arquivo.type);
    evidenciaKey = `reports/${cnes}/${Date.now()}-${crypto.randomUUID()}.${ext}`;
    await env.EVIDENCIAS.put(evidenciaKey, arquivo.stream(), {
      httpMetadata: { contentType: arquivo.type },
    });
  }

  await env.DB.prepare(
    `INSERT INTO reports
       (cnes, nome, tipo, texto, lat, lon,
        rua_correta, numero_correto, bairro_correto, lat_sugerida, lon_sugerida,
        evidencia_key, ip_hash, criado_em)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))`
  ).bind(cnes, nome, tipo, texto, lat, lon,
         ruaCorreta || null, numeroCorreto || null, bairroCorreto || null, latSug, lonSug,
         evidenciaKey, ipHash).run();

  return json({ ok: true });
}

// GET só existe para checagem manual/humana de que a rota está viva; não
// expõe dado nenhum do banco.
export async function onRequestGet() {
  return json({ ok: true, rota: "POST /api/report" });
}
