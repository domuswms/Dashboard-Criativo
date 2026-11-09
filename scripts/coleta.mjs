// Coleta diária do ClickUp para data/clickup.json.
// Modo automático: o script busca na API do ClickUp (CLICKUP_TOKEN) e faz tudo sozinho.
// Modo manual: a rotina chama o MCP do ClickUp e grava cada página em .coleta/; este script
// diz o que buscar, valida o que foi gravado e mescla no arquivo de dados.
//
//   node scripts/coleta.mjs auto [--completa]    busca na API, valida e grava data/clickup.json
//   node scripts/coleta.mjs plano [--completa]   prepara a coleta e lista as páginas 0
//   node scripts/coleta.mjs verificar            valida as páginas e diz se falta alguma
//   node scripts/coleta.mjs mesclar              grava data/clickup.json
//   node scripts/coleta.mjs enviar               envia data/clickup.json à planilha (Apps Script)
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const DADOS = path.join(RAIZ, 'data', 'clickup.json');
const TMP = path.join(RAIZ, '.coleta');
const ESTADO = path.join(TMP, 'estado.json');
const WORKSPACE = '90131376764'; // Domus Ecommerce
const API = process.env.CLICKUP_API_URL || 'https://api.clickup.com/api/v2';
const TENTATIVAS = 3;
const MAX_PAG = 10, POR_PAG = 100, LIMITE = MAX_PAG * POR_PAG; // mesmo teto da página: 10 páginas de 100
const MARGEM = 60 * 60 * 1000; // 1 h de folga na coleta incremental
const FONTES = {
  anuncios: { nome: 'Anúncios (Criativo)', filtro: { list_ids: ['901312757364'] } },
  compras: { nome: 'Compras', filtro: { list_ids: ['901312319816'] } },
  itajai: { nome: 'Pasta Itajaí-SC', filtro: { folder_ids: ['90137504399'] } },
  londrina: { nome: 'Pasta Londrina-PR', filtro: { folder_ids: ['90137507791'] } },
};

const ler = f => JSON.parse(fs.readFileSync(f, 'utf8'));
const params = (k, p) => ({ workspace_id: WORKSPACE, ...FONTES[k].filtro, include_closed: true, order_by: 'updated', page: p });
const arq = (k, p) => path.join(TMP, `${k}-${p}.json`);
const rel = f => path.relative(RAIZ, f).replace(/\\/g, '/');
const sair = (msg, cod = 1) => { console.log(msg); process.exit(cod) };

function plano(completa, silencioso) {
  const atual = fs.existsSync(DADOS) ? ler(DADOS) : { fontes: {} };
  fs.rmSync(TMP, { recursive: true, force: true });
  fs.mkdirSync(TMP, { recursive: true });
  const estado = { inicio: Date.now(), fontes: {} };
  for (const k of Object.keys(FONTES)) {
    const sinc = atual.fontes?.[k]?.sincronizado_em;
    estado.fontes[k] = completa || !sinc ? { modo: 'completa', desde: null } : { modo: 'incremental', desde: sinc - MARGEM };
  }
  fs.writeFileSync(ESTADO, JSON.stringify(estado, null, 2));
  if (silencioso) return estado;
  console.log('Coleta preparada. Para cada fonte, chame clickup_filter_tasks com os parâmetros abaixo e grave');
  console.log('a resposta da ferramenta, sem alterar nada, no arquivo indicado. Depois rode: node scripts/coleta.mjs verificar\n');
  for (const [k, e] of Object.entries(estado.fontes)) {
    console.log(`${k} (${e.modo}${e.desde ? ', alteradas desde ' + new Date(e.desde).toISOString() : ''})`);
    console.log(`  parâmetros: ${JSON.stringify(params(k, 0))}`);
    console.log(`  gravar em:  ${rel(arq(k, 0))}`);
  }
}

// Confere uma página gravada. Devolve a lista de problemas (vazia se estiver ok).
function validar(k, p, d) {
  const e = [], lista = FONTES[k].filtro.list_ids?.[0], num = /^\d+$/;
  if (!d || !Array.isArray(d.tasks)) return ['falta o array "tasks"'];
  if (d.page !== p) e.push(`"page" é ${d.page}, esperado ${p}`);
  if (typeof d.has_more !== 'boolean') e.push('"has_more" ausente');
  if (d.count !== d.tasks.length) e.push(`"count" (${d.count}) difere do número de tarefas (${d.tasks.length})`);
  if (d.has_more && d.tasks.length !== POR_PAG) e.push(`página com has_more=true deveria ter ${POR_PAG} tarefas`);
  const ids = new Set();
  d.tasks.forEach((t, i) => {
    const q = `tarefa ${i} (${t?.id})`;
    if (!t || typeof t.id !== 'string' || !t.id) return e.push(`tarefa ${i} sem id`);
    if (ids.has(t.id)) e.push(`${q} repetida`); ids.add(t.id);
    if (typeof t.name !== 'string') e.push(`${q} sem name`);
    if (typeof t.status !== 'string') e.push(`${q} sem status`);
    if (t.url !== `https://app.clickup.com/t/${t.id}`) e.push(`${q} com url diferente do id`);
    if (!num.test(t.date_updated ?? '')) e.push(`${q} com date_updated inválido`);
    for (const c of ['date_closed', 'due_date']) if (t[c] != null && !num.test(t[c])) e.push(`${q} com ${c} inválido`);
    if (!Array.isArray(t.assignees) || t.assignees.some(a => a?.username !== null && typeof a?.username !== 'string')) e.push(`${q} com assignees inválido`);
    if (!Array.isArray(t.tags) || t.tags.some(g => typeof g?.name !== 'string')) e.push(`${q} com tags inválido`);
    if (lista && t.list?.id !== lista) e.push(`${q} não é da lista ${lista}`);
    if (i && +t.date_updated > +d.tasks[i - 1].date_updated) e.push(`${q} fora da ordem por date_updated (a ordem original foi alterada?)`);
  });
  return e;
}

// Lê as páginas gravadas de uma fonte e diz se a coleta dela terminou.
function situacao(k, e) {
  const tarefas = [];
  for (let p = 0; ; p++) {
    const f = arq(k, p);
    if (!fs.existsSync(f)) return { falta: p, tarefas };
    let d;
    try { d = ler(f) } catch (x) { return { pagina: p, erro: `${rel(f)} não é JSON válido: ${x.message}` } }
    const prob = validar(k, p, d);
    if (prob.length) return { pagina: p, erro: `${rel(f)}: ${prob.slice(0, 5).join('; ')}${prob.length > 5 ? ` (+${prob.length - 5})` : ''}` };
    tarefas.push(...d.tasks);
    const antigas = e.desde != null && d.tasks.length && +d.tasks[d.tasks.length - 1].date_updated < e.desde;
    if (!d.has_more || antigas || p + 1 >= MAX_PAG) return { ok: true, paginas: p + 1, tarefas };
  }
}

function estado() {
  if (!fs.existsSync(ESTADO)) sair('Rode primeiro: node scripts/coleta.mjs plano');
  return ler(ESTADO);
}

function verificar() {
  const est = estado();
  let pendente = false;
  for (const [k, e] of Object.entries(est.fontes)) {
    const s = situacao(k, e);
    if (s.ok) console.log(`${k}: OK (${s.paginas} página(s), ${s.tarefas.length} tarefas)`);
    else {
      pendente = true;
      if (s.erro) console.log(`${k}: ERRO ${s.erro}\n  refaça a chamada dessa página e grave a resposta de novo, sem alterar nada`);
      else console.log(`${k}: BUSCAR página ${s.falta}\n  parâmetros: ${JSON.stringify(params(k, s.falta))}\n  gravar em:  ${rel(arq(k, s.falta))}`);
    }
  }
  if (pendente) sair('\nAinda há páginas a buscar ou corrigir. Depois rode verificar de novo.');
  console.log('\nTudo certo. Rode: node scripts/coleta.mjs mesclar');
}

function mesclar() {
  const est = estado();
  const atual = fs.existsSync(DADOS) ? ler(DADOS) : { fontes: {} };
  const saida = { gerado_em: new Date(est.inicio).toISOString(), workspace_id: WORKSPACE, fontes: {} };
  for (const [k, e] of Object.entries(est.fontes)) {
    const s = situacao(k, e);
    if (!s.ok) sair(`${k} ainda não está completa. Rode verificar.`);
    const m = new Map(e.modo === 'completa' ? [] : (atual.fontes?.[k]?.tarefas || []).map(t => [t.id, t]));
    let novas = 0, alteradas = 0;
    for (const t of s.tarefas) {
      const v = m.get(t.id);
      if (!v) novas++; else if (JSON.stringify(v) !== JSON.stringify(t)) alteradas++;
      m.set(t.id, t);
    }
    const tarefas = [...m.values()].sort((a, b) => +b.date_updated - +a.date_updated).slice(0, LIMITE);
    saida.fontes[k] = { nome: FONTES[k].nome, sincronizado_em: est.inicio, modo: e.modo, tarefas };
    console.log(`${k}: ${e.modo}, ${novas} nova(s), ${alteradas} alterada(s), ${tarefas.length} no arquivo`);
  }
  // Uma tarefa por linha, para o histórico do git mostrar o que mudou.
  const fonte = ([k, f]) => `    ${JSON.stringify(k)}: {"nome": ${JSON.stringify(f.nome)}, "sincronizado_em": ${f.sincronizado_em}, "modo": ${JSON.stringify(f.modo)}, "tarefas": [\n${f.tarefas.map(t => '      ' + JSON.stringify(t)).join(',\n')}\n    ]}`;
  const txt = `{\n  "gerado_em": ${JSON.stringify(saida.gerado_em)},\n  "workspace_id": ${JSON.stringify(WORKSPACE)},\n  "fontes": {\n${Object.entries(saida.fontes).map(fonte).join(',\n')}\n  }\n}\n`;
  JSON.parse(txt);
  fs.mkdirSync(path.dirname(DADOS), { recursive: true });
  fs.writeFileSync(DADOS, txt);
  console.log(`\n${rel(DADOS)} gravado (${saida.gerado_em}).`);
}

// Uma página da API do ClickUp, no mesmo formato da resposta de clickup_filter_tasks do conector,
// para que verificar e mesclar valham igual nos dois modos.
async function buscarPagina(k, p) {
  const q = new URLSearchParams({ include_closed: 'true', subtasks: 'true', order_by: 'updated', page: String(p) });
  for (const id of FONTES[k].filtro.list_ids || []) q.append('list_ids[]', id);
  for (const id of FONTES[k].filtro.folder_ids || []) q.append('project_ids[]', id); // pasta = "project" na API v2
  const r = await fetch(`${API}/team/${WORKSPACE}/task?${q}`, { headers: { Authorization: process.env.CLICKUP_TOKEN } });
  if (!r.ok) throw Object.assign(new Error(`HTTP ${r.status}: ${(await r.text()).slice(0, 200)}`), { status: r.status });
  const d = await r.json();
  if (!Array.isArray(d.tasks)) throw new Error('resposta sem "tasks"');
  const tasks = d.tasks.map(t => ({
    id: t.id, custom_id: t.custom_id ?? null, name: t.name, status: t.status?.status, url: t.url,
    priority: t.priority?.priority ?? null,
    assignees: (t.assignees || []).map(a => ({ id: a.id, username: a.username ?? null })),
    tags: (t.tags || []).map(g => ({ name: g.name })),
    due_date: t.due_date ?? null, date_updated: t.date_updated, date_closed: t.date_closed ?? null,
    list: { id: t.list?.id, name: t.list?.name },
  }));
  const mais = typeof d.last_page === 'boolean' ? !d.last_page : tasks.length === POR_PAG;
  return { tasks, count: tasks.length, page: p, has_more: mais, next_page: mais ? p + 1 : null };
}

async function auto(completa) {
  if (!process.env.CLICKUP_TOKEN) sair('Coleta automática indisponível: CLICKUP_TOKEN não definido. Siga o modo manual do ROTINA.md.', 3);
  const est = plano(completa, true);
  for (const [k, e] of Object.entries(est.fontes)) {
    const vezes = {};
    let ultimo = '';
    for (;;) {
      const s = situacao(k, e);
      if (s.ok) { console.log(`${k}: OK (${e.modo}, ${s.paginas} página(s), ${s.tarefas.length} tarefas)`); break; }
      const p = s.falta ?? s.pagina;
      if (s.erro) {
        ultimo = s.erro;
        console.log(`${k}: página ${p} não conferiu: ${s.erro}`);
        fs.rmSync(arq(k, p), { force: true });
      }
      vezes[p] = (vezes[p] || 0) + 1;
      if (vezes[p] > TENTATIVAS) sair(`ERRO ${k}, página ${p}, após ${TENTATIVAS} tentativas: ${ultimo}\nNada foi gravado em ${rel(DADOS)}.`);
      try {
        fs.writeFileSync(arq(k, p), JSON.stringify(await buscarPagina(k, p)));
      } catch (x) {
        ultimo = x.message;
        console.log(`${k}: página ${p} falhou (tentativa ${vezes[p]}): ${x.message}`);
        if (x.status === 401) sair(`ERRO ${k}, página ${p}: ${x.message}. Confira o CLICKUP_TOKEN. Nada foi gravado em ${rel(DADOS)}.`);
        if (vezes[p] < TENTATIVAS) await new Promise(ok => setTimeout(ok, (x.status === 429 ? 30000 : 5000) * vezes[p]));
      }
    }
  }
  console.log('');
  mesclar();
}

// Envia o arquivo de dados ao Web App do Apps Script, que atualiza a planilha pelo ID da tarefa.
// Variáveis de ambiente: APPS_SCRIPT_URL (URL /exec do Web App) e APPS_SCRIPT_TOKEN.
async function enviar() {
  const url = process.env.APPS_SCRIPT_URL, token = process.env.APPS_SCRIPT_TOKEN;
  if (!url || !token) sair('Envio à planilha pulado: defina APPS_SCRIPT_URL e APPS_SCRIPT_TOKEN.', 0);
  if (!fs.existsSync(DADOS)) sair('Falta data/clickup.json. Rode mesclar antes.');
  const d = ler(DADOS);
  const corpo = { token, gerado_em: d.gerado_em,
    fontes: Object.fromEntries(Object.entries(d.fontes).map(([k, v]) => [k, { tarefas: v.tarefas }])) };
  let r;
  try {
    // text/plain evita a pré-checagem CORS; o Apps Script responde com redirecionamento, que o fetch segue.
    r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'text/plain;charset=utf-8' },
      body: JSON.stringify(corpo), redirect: 'follow' });
  } catch (e) { sair(`ERRO ao enviar à planilha: ${e.message}`); }
  const texto = await r.text();
  let res; try { res = JSON.parse(texto) } catch { sair(`ERRO: resposta inesperada (HTTP ${r.status}): ${texto.slice(0, 200)}`) }
  if (!r.ok || !res.ok) sair(`ERRO da planilha: ${res.erro || 'HTTP ' + r.status}`);
  console.log(`Planilha atualizada: ${res.novas} nova(s), ${res.atualizadas} atualizada(s), ${res.mudancas_de_status} mudança(s) de status, ${res.total} no total.`);
}

const [cmd, ...arg] = process.argv.slice(2);
if (cmd === 'auto') await auto(arg.includes('--completa'));
else if (cmd === 'plano') plano(arg.includes('--completa'));
else if (cmd === 'verificar') verificar();
else if (cmd === 'mesclar') mesclar();
else if (cmd === 'enviar') await enviar();
else sair('Uso: node scripts/coleta.mjs auto [--completa] | plano [--completa] | verificar | mesclar | enviar');
