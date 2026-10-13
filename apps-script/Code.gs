/**
 * Banco de dados do dashboard Cadastro & Criativo.
 * Web App ligado à planilha "banco-de-dados": recebe a coleta diária do ClickUp e a grava em
 * clickup_tarefas (uma linha por tarefa, atualizada pelo ID) e clickup_historico (mudanças de status).
 *
 * Instalação: veja apps-script/README.md.
 * Propriedade obrigatória (Configurações do projeto > Propriedades do script): TOKEN.
 */

var ABA_TAREFAS = 'clickup_tarefas';
var ABA_HISTORICO = 'clickup_historico';
var COLUNAS_TAREFAS = 14; // ID .. Coletada em
var ABAS_LEITURA = ['clickup_tarefas', 'clickup_historico', 'plano_90_dias', 'fornecedores',
  'posicoes_fornecedor', 'vonder_60', 'lotes', 'metas_base', 'relatorios'];

function doPost(e) {
  var lock = LockService.getScriptLock();
  try {
    lock.waitLock(30000);
    var corpo = JSON.parse(e.postData.contents);
    if (!tokenValido_(corpo.token)) return json_({ ok: false, erro: 'token inválido' });
    return json_(receberClickup_(corpo));
  } catch (err) {
    return json_({ ok: false, erro: String(err && err.message || err) });
  } finally {
    lock.releaseLock();
  }
}

// Leitura de uma aba: ?token=...&aba=plano_90_dias (para análises e para o dashboard).
function doGet(e) {
  var p = (e && e.parameter) || {};
  if (!tokenValido_(p.token)) return json_({ ok: false, erro: 'token inválido' });
  if (!p.aba) return json_({ ok: true, abas: ABAS_LEITURA });
  if (ABAS_LEITURA.indexOf(p.aba) < 0) return json_({ ok: false, erro: 'aba não permitida' });
  var sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(p.aba);
  if (!sh) return json_({ ok: false, erro: 'aba não encontrada' });
  var v = sh.getDataRange().getValues();
  var tz = Session.getScriptTimeZone();
  var linhas = v.slice(1).map(function (r) {
    return r.map(function (c) {
      return c instanceof Date ? Utilities.formatDate(c, tz, "yyyy-MM-dd'T'HH:mm:ss") : c;
    });
  });
  return json_({ ok: true, aba: p.aba, cabecalho: v[0], linhas: linhas });
}

function receberClickup_(corpo) {
  if (!corpo.fontes) throw new Error('payload sem "fontes"');
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName(ABA_TAREFAS);
  var hist = ss.getSheetByName(ABA_HISTORICO);
  if (!sh || !hist) throw new Error('faltam as abas ' + ABA_TAREFAS + ' e/ou ' + ABA_HISTORICO);

  var coleta = new Date(corpo.gerado_em);
  var ultima = sh.getLastRow();
  var atuais = ultima > 1 ? sh.getRange(2, 1, ultima - 1, COLUNAS_TAREFAS).getValues() : [];
  var indice = {};
  atuais.forEach(function (r, i) { indice[r[0]] = i; });

  var novas = [], mudancas = [], atualizadas = 0, vistos = {};
  Object.keys(corpo.fontes).forEach(function (fonte) {
    (corpo.fontes[fonte].tarefas || []).forEach(function (t) {
      if (vistos[t.id]) return; // a mesma tarefa pode aparecer em duas fontes: vale a primeira
      vistos[t.id] = true;
      var linha = montarLinha_(fonte, t, coleta);
      if (Object.prototype.hasOwnProperty.call(indice, t.id)) {
        var i = indice[t.id], antiga = atuais[i];
        if (String(antiga[3]) !== String(linha[3])) mudancas.push([coleta, t.id, fonte, antiga[3], linha[3]]);
        atuais[i] = linha;
        atualizadas++;
      } else {
        novas.push(linha);
      }
    });
  });

  if (atuais.length) sh.getRange(2, 1, atuais.length, COLUNAS_TAREFAS).setValues(atuais);
  if (novas.length) sh.getRange(atuais.length + 2, 1, novas.length, COLUNAS_TAREFAS).setValues(novas);
  if (mudancas.length) hist.getRange(Math.max(hist.getLastRow() + 1, 3), 1, mudancas.length, 5).setValues(mudancas);

  return { ok: true, novas: novas.length, atualizadas: atualizadas, mudancas_de_status: mudancas.length,
    total: atuais.length + novas.length };
}

// Mesmas colunas da aba clickup_tarefas gerada por scripts/gerar_planilha.py.
function montarLinha_(fonte, t, coleta) {
  var tags = (t.tags || []).map(function (x) { return x.name; });
  var resp = (t.assignees || []).map(function (a) { return a.username || ''; }).join(', ');
  return [t.id, fonte, t.name, t.status, resp, tags.join(', '), t.priority || '',
    data_(t.due_date), data_(t.date_updated), data_(t.date_closed),
    (t.list && t.list.name) || '', filial_(fonte, tags), t.url, coleta];
}

function filial_(fonte, tags) {
  var t = tags.map(function (x) { return String(x).toLowerCase(); });
  if (fonte === 'itajai' || t.indexOf('itajai') >= 0 || t.indexOf('itajaí') >= 0) return 'Itajaí';
  if (fonte === 'londrina' || t.indexOf('londrina') >= 0) return 'Londrina';
  return '';
}

function data_(ms) { return ms ? new Date(Number(ms)) : ''; }

function tokenValido_(token) {
  var esperado = PropertiesService.getScriptProperties().getProperty('TOKEN');
  if (!esperado || !token) return false;
  token = String(token);
  if (token.length !== esperado.length) return false;
  var d = 0;
  for (var i = 0; i < token.length; i++) d |= token.charCodeAt(i) ^ esperado.charCodeAt(i);
  return d === 0;
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
