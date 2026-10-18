// Cloudflare Pages Function — POST /api/report
//
// Recebe o report de localização enviado pelo botão da ficha (ver
// web/index.html, seção "reportar localização") e grava:
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
const LIMITE_EVIDENCIA = 1024 * 1024; // 1 MB — mesmo limite validado no cliente
const JANELA_LIMITE_MINUTOS = 10;
const MAX_REPORTS_NA_JANELA = 5; // por IP, contra abuso básico

// Limites específicos de anexo. O teto de reports acima contém spam de texto,
// que é barato; anexo é caro em armazenamento, então tem contenção própria.
// Com 1 MB por imagem, o pior caso de abuso fica em 500 MB por dia — dentro da
// camada gratuita de 10 GB do R2 mesmo se durar o mês inteiro.
const MAX_ANEXOS_POR_IP_DIA = 10;
const MAX_ANEXOS_GLOBAL_DIA = 500;

// Teto do site inteiro: todos os reports, com ou sem foto, nas últimas 24 h.
// O limite por IP não segura muitos IPs juntos enchendo o banco; um dia normal
// tem poucos reports, e este número só existe para conter abuso.
const MAX_REPORTS_GLOBAL_DIA = 2000;

// De onde o envio pode vir. O navegador manda o cabeçalho Origin em todo POST
// feito por página; sem esta conferência, qualquer outro site poderia fazer o
// navegador de quem o visita enviar reports para cá. As prévias de deploy do
// Cloudflare Pages vêm em <hash>.onde-tem-sus.pages.dev. Quando o site ganhar
// domínio próprio, ele entra aqui. Sem Origin nenhum (curl, script) a
// conferência não se aplica: os limites de taxa continuam valendo.
const SITE = "onde-tem-sus.pages.dev";
const ORIGENS_LOCAIS = new Set(["http://localhost:8788", "http://127.0.0.1:8788"]);
function origemPermitida(origem) {
  if (!origem) return true;
  if (ORIGENS_LOCAIS.has(origem)) return true;
  try {
    const u = new URL(origem);
    return u.protocol === "https:" &&
           (u.hostname === SITE || u.hostname.endsWith("." + SITE));
  } catch {
    return false;
  }
}

function json(dados, status = 200) {
  return new Response(JSON.stringify(dados), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  });
}

// O IP não é guardado: guarda-se um HMAC dele, que serve só para contar
// envios do mesmo endereço nos limites de taxa abaixo.
//
// Um SHA-256 simples não bastava. São 4,3 bilhões de IPv4 e o prefixo estava
// no código público: calcular o hash de todos leva minutos, e cada report
// voltaria a apontar para um IP. Com HMAC, a conta exige o SEGREDO_IP, que
// existe só na configuração da Cloudflare — nem no repositório, nem no log.
//
// A data do dia entra na mensagem: o mesmo IP gera um valor diferente a cada
// dia, então nem quem tiver o banco consegue seguir uma pessoa ao longo do
// tempo. Os limites olham no máximo 24 h para trás e continuam valendo; a
// virada do dia (UTC) apenas recomeça a contagem.
async function hashIp(ip, segredo) {
  const enc = new TextEncoder();
  const chave = await crypto.subtle.importKey(
    "raw", enc.encode(segredo), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const dia = new Date().toISOString().slice(0, 10);
  const buf = await crypto.subtle.sign("HMAC", chave, enc.encode(dia + "::" + ip));
  return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, "0")).join("");
}

// Falha do banco ou do bucket: o detalhe vai para o log da Cloudflare, e o
// formulário mostra a mensagem do campo "erro". 503 diz "tente de novo", que é
// o que se espera de uma falha passageira.
function falhaDeServidor(etapa, e) {
  console.error(`report: falha na ${etapa}:`, e && e.message);
  return json({ erro: "não foi possível salvar o report agora, tente de novo em instantes" }, 503);
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

// O tipo do anexo sai do CONTEÚDO, nunca do nome do arquivo nem do tipo que
// o navegador declara — os dois vêm do cliente e podem ser qualquer coisa: um
// SVG (que carrega script) passava por "image/", e um "foto.html" declarado
// como PNG era gravado com extensão .html. Só três formatos, reconhecidos
// pela assinatura dos primeiros bytes; a extensão e o tipo gravados no R2
// saem daqui.
function formatoPelaAssinatura(b) {
  if (b.length >= 3 && b[0] === 0xFF && b[1] === 0xD8 && b[2] === 0xFF)
    return { ext: "jpg", mime: "image/jpeg" };
  const PNG = [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A];
  if (b.length >= 8 && PNG.every((x, k) => b[k] === x))
    return { ext: "png", mime: "image/png" };
  const asc = (ini, fim) => String.fromCharCode(...b.slice(ini, fim));
  if (b.length >= 12 && asc(0, 4) === "RIFF" && asc(8, 12) === "WEBP")
    return { ext: "webp", mime: "image/webp" };
  return null;
}

export async function onRequestPost(context) {
  const { request, env } = context;

  if (!origemPermitida(request.headers.get("Origin"))) {
    return json({ erro: "origem não permitida" }, 403);
  }

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
  // O nome vem do formulário e quem envia pode trocá-lo: serve só de lembrete
  // para quem revisa. O nome oficial é o do CNES, pelo código.
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

  // Sem o segredo a rota RECUSA, em vez de voltar calada a um hash que
  // qualquer um reverte. O motivo vai para o log, nunca o valor do segredo.
  if (!env.SEGREDO_IP) {
    console.error("SEGREDO_IP não configurado: report recusado");
    return json({ erro: "servidor sem configuração para receber reports" }, 500);
  }
  const ip = request.headers.get("CF-Connecting-IP") || "desconhecido";
  const ipHash = await hashIp(ip, env.SEGREDO_IP);

  // limite básico de taxa: sem isso, um script poderia inundar o banco/bucket
  // a janela é calculada pelo próprio SQLite: criado_em é gravado por
  // datetime('now') ("2026-08-31 13:39:51"), formato diferente do ISO do
  // JavaScript ("2026-08-31T13:39:51.000Z"). Como a comparação é textual,
  // misturar os dois faz o filtro nunca casar e o limite não valer nada.
  //
  // Contar e gravar não são uma operação só: k requisições exatamente
  // simultâneas do mesmo IP podem contar antes de qualquer gravação e passar
  // todas, estourando o limite em até k-1. Vale também para o teto global e
  // para os de anexo. Para conter abuso, basta.
  //
  // Primeiro o limite do IP, que lê só os últimos 10 minutos. O teto do dia lê
  // as linhas de 24 h, e o banco cobra por linha lida: contado para todo envio,
  // um IP já bloqueado poderia gastar a cota diária só levando 429.
  try {
    const { results } = await env.DB.prepare(
      `SELECT COUNT(*) AS n FROM reports
        WHERE ip_hash = ? AND criado_em >= datetime('now', ?)`
    ).bind(ipHash, `-${JANELA_LIMITE_MINUTOS} minutes`).all();
    if ((results?.[0]?.n ?? 0) >= MAX_REPORTS_NA_JANELA) {
      return json({ erro: "muitos reports em pouco tempo, tente novamente mais tarde" }, 429);
    }
    const { results: dia } = await env.DB.prepare(
      `SELECT COUNT(*) AS n FROM reports WHERE criado_em >= datetime('now', '-1 day')`
    ).all();
    if ((dia?.[0]?.n ?? 0) >= MAX_REPORTS_GLOBAL_DIA) {
      return json({ erro: "o site recebeu muitos reports hoje, tente novamente mais tarde" }, 429);
    }
  } catch (e) {
    return falhaDeServidor("contagem dos limites", e);
  }

  // ---- evidência (opcional) --------------------------------------------------
  // Estourar o limite de anexo NÃO descarta o report: o texto e a correção de
  // endereço são o que interessa, e perder tudo por causa da foto seria punir
  // quem quis ajudar. A imagem é recusada e o cliente avisa que só ela ficou de
  // fora.
  let evidenciaKey = null;
  let anexo = "nenhum";
  const arquivo = form.get("evidencia");
  // Anexo recusado por tipo ou tamanho também NÃO derruba o report, pelo
  // mesmo motivo do limite diário: o texto é o que interessa.
  const formato = (arquivo && typeof arquivo === "object" && arquivo.size > 0)
    ? formatoPelaAssinatura(new Uint8Array(await arquivo.slice(0, 12).arrayBuffer()))
    : undefined;
  if (formato === null) {
    anexo = "recusado_tipo";
  } else if (formato && arquivo.size > LIMITE_EVIDENCIA) {
    anexo = "recusado_tamanho";
  } else if (formato) {
    // A contagem falhar custa só a foto, como o put falhar: o texto segue.
    let noDia = null;
    try {
      const { results: contas } = await env.DB.prepare(
        `SELECT
           COUNT(*) AS global,
           SUM(CASE WHEN ip_hash = ? THEN 1 ELSE 0 END) AS meus
         FROM reports
         WHERE evidencia_key IS NOT NULL
           AND criado_em >= datetime('now', '-1 day')`
      ).bind(ipHash).all();
      noDia = contas?.[0] || {};
    } catch (e) {
      console.error("report: falha na contagem de anexos:", e && e.message);
    }
    if (!noDia) {
      anexo = "recusado_falha";
    } else if ((noDia.meus ?? 0) >= MAX_ANEXOS_POR_IP_DIA ||
        (noDia.global ?? 0) >= MAX_ANEXOS_GLOBAL_DIA) {
      anexo = "recusado_limite";
    } else {
      evidenciaKey = `reports/${cnes}/${Date.now()}-${crypto.randomUUID()}.${formato.ext}`;
      try {
        await env.EVIDENCIAS.put(evidenciaKey, arquivo.stream(), {
          httpMetadata: { contentType: formato.mime },
        });
        anexo = "gravado";
      } catch (e) {
        // a foto falhou, o report não: segue sem ela, e o cliente avisa
        console.error("falha ao gravar a evidência no R2:", e && e.message);
        evidenciaKey = null;
        anexo = "recusado_falha";
      }
    }
  }

  // A foto já está no R2 quando a linha é gravada, porque a linha guarda a
  // chave dela. Se a gravação falhar, a foto acabada de subir é apagada na
  // hora: sem isso sobraria no bucket uma imagem de alguém sem report nenhum.
  try {
    await env.DB.prepare(
      `INSERT INTO reports
         (cnes, nome, tipo, texto, lat, lon,
          rua_correta, numero_correto, bairro_correto, lat_sugerida, lon_sugerida,
          evidencia_key, ip_hash, criado_em)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))`
    ).bind(cnes, nome, tipo, texto, lat, lon,
           ruaCorreta || null, numeroCorreto || null, bairroCorreto || null, latSug, lonSug,
           evidenciaKey, ipHash).run();
  } catch (e) {
    if (evidenciaKey) {
      try { await env.EVIDENCIAS.delete(evidenciaKey); }
      catch (e2) { console.error("evidência órfã, apagar à mão:", evidenciaKey, e2 && e2.message); }
    }
    return falhaDeServidor("gravação do report", e);
  }

  // O código de conexão só serve aos limites acima, que olham no máximo 24 h
  // para trás. Passados 2 dias ele não protege mais nada, então sai — e sai
  // aqui, a cada report recebido, porque as Pages Functions não têm
  // agendamento e um comando manual dependeria de alguém lembrar de rodar.
  // É o prazo que a página Sobre (seção Privacidade) promete.
  // A limpeza falhar não desfaz o report já gravado: fica para o próximo.
  try {
    await env.DB.prepare(
      `UPDATE reports SET ip_hash = NULL
        WHERE ip_hash IS NOT NULL AND criado_em < datetime('now', '-2 days')`
    ).run();
  } catch (e) {
    console.error("falha ao apagar códigos de conexão antigos:", e && e.message);
  }

  return json({ ok: true, anexo });
}

// GET só existe para checagem manual/humana de que a rota está viva; não
// expõe dado nenhum do banco.
export async function onRequestGet() {
  return json({ ok: true, rota: "POST /api/report" });
}
