#!/usr/bin/env python3
"""Gera planilha/banco-de-dados.xlsx: banco de dados do dashboard Cadastro & Criativo.

Uso: python3 scripts/gerar_planilha.py
Lê data/clickup.json (carga inicial da aba clickup_tarefas) e escreve a planilha.
Depois de gerar, rode o recalc.py da skill de xlsx para gravar os valores das fórmulas.
"""
import json
from datetime import datetime, timedelta, date, timezone
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "planilha" / "banco-de-dados.xlsx"
FONTE = "Arial"
LIME = "ECFC30"
INK = "212121"
ULT = 1000  # última linha coberta pelas fórmulas

f_norm = Font(name=FONTE, size=10)
f_in = Font(name=FONTE, size=10, color="0000FF")  # entrada manual (azul)
f_head = Font(name=FONTE, size=10, bold=True, color=INK)
f_tit = Font(name=FONTE, size=14, bold=True, color=INK)
f_ex = Font(name=FONTE, size=10, italic=True, color="7F7F7F")
f_nota = Font(name=FONTE, size=9, italic=True, color="595959")
fill_head = PatternFill("solid", fgColor=LIME)
fill_ex = PatternFill("solid", fgColor="EDEDED")
fill_in = PatternFill("solid", fgColor="FFFF99")
borda = Border(bottom=Side(style="thin", color="BFBFBF"))
DATA = "dd/mm/yyyy"
PCT = "0.0%"


def cabecalho(ws, cols, larguras):
    for i, (c, w) in enumerate(zip(cols, larguras), 1):
        x = ws.cell(row=1, column=i, value=c)
        x.font, x.fill = f_head, fill_head
        x.alignment = Alignment(wrap_text=True, vertical="center")
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[1].height = 32
    ws.freeze_panes = "A2"


def exemplo(ws, valores, fmts=None):
    """Linha 2: exemplo de formato, em cinza. Os dados reais começam na linha 3."""
    for i, v in enumerate(valores, 1):
        c = ws.cell(row=2, column=i, value=v)
        c.font, c.fill = f_ex, fill_ex
        if fmts and fmts.get(i):
            c.number_format = fmts[i]


def entrada(ws, faixa, fmt=None):
    for linha in ws[faixa]:
        for c in linha:
            c.font = f_in
            if fmt:
                c.number_format = fmt


def lista(ws, faixa, itens):
    dv = DataValidation(type="list", formula1='"' + ",".join(itens) + '"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(faixa)


def ms_para_data(ms, com_hora=True):
    if not ms:
        return None
    d = datetime.fromtimestamp(int(ms) / 1000, timezone.utc).replace(tzinfo=None) - timedelta(hours=3)  # horário de Brasília
    return d if com_hora else d.date()


def filial(fonte, tags):
    t = {x.lower() for x in tags}
    if fonte == "itajai" or t & {"itajai", "itajaí"}:
        return "Itajaí"
    if fonte == "londrina" or "londrina" in t:
        return "Londrina"
    return ""


wb = Workbook()

# ---------------------------------------------------------------- LEIA-ME
ws = wb.active
ws.title = "LEIA-ME"
ws.column_dimensions["A"].width = 30
ws.column_dimensions["B"].width = 110
ws["A1"] = "Banco de dados · Cadastro & Criativo"
ws["A1"].font = f_tit
linhas = [
    ("Como usar", ""),
    ("Cores", "Texto azul = digitação manual. Preto = fórmula (não editar). Linha 2 cinza de cada aba = exemplo de formato; os dados reais começam na linha 3."),
    ("Fórmulas", f"As fórmulas cobrem até a linha {ULT}. Não deixe linhas em branco no meio dos dados."),
    ("", ""),
    ("Abas", ""),
    ("clickup_tarefas", "Carga inicial das tarefas do ClickUp (data/clickup.json de 13/10/2026). Daqui em diante a rotina diária acrescenta tarefas novas e atualiza as existentes pelo ID, sem duplicar."),
    ("clickup_historico", "Uma linha a cada mudança de status detectada pela rotina. Serve para medir quanto tempo a tarefa ficou em cada etapa."),
    ("plano_90_dias", "Plano de 90 dias: uma linha por atividade, com fase, responsável, prazo, status e peso. O percentual do plano é calculado pelo peso."),
    ("fornecedores", "Cadastro de fornecedores. Os números de catálogo, cadastrados e disponíveis aparecem sozinhos, a partir da posição mais recente."),
    ("posicoes_fornecedor", "Registro de posições por fornecedor e data: produtos no catálogo, cadastrados no ERP e disponíveis para venda. Preenchido só pelo time de cadastro."),
    ("fornecedor_painel", "Escolha o fornecedor na célula amarela e veja catálogo, cadastrados, disponíveis, o que falta cadastrar e as coberturas."),
    ("vonder_60", "Projeto Vonder 60: posições periódicas de anúncios publicados e no ERP, com a variação entre posições e a meta."),
    ("lotes", "Lotes de cadastro (planilhas recebidas): datas de recebimento, início e conclusão, e devoluções. Base do tempo médio de execução."),
    ("metas_base", "Valores de base e metas planejadas de cada indicador. Estão em branco: só preencha o que a gestão aprovou."),
    ("relatorios", "Planejado × realizado, com fórmulas lendo as demais abas."),
    ("", ""),
    ("Limites conhecidos", ""),
    ("Tempo de execução", "O ClickUp devolvido pela rotina não traz a data de criação da tarefa. Por isso o tempo médio de execução vem da aba lotes (início → conclusão). Para tarefas do ClickUp, o tempo só será confiável depois que clickup_historico acumular mudanças de status."),
    ("Prazo cumprido", "Considera só tarefas concluídas que têm prazo. Concluída no dia do prazo conta como no prazo."),
    ("Filial", "Vem da fonte (Itajaí, Londrina) ou da tag da tarefa. Tarefas sem essa informação ficam sem filial."),
]
for i, (a, b) in enumerate(linhas, 3):
    ws.cell(row=i, column=1, value=a).font = Font(name=FONTE, size=10, bold=True)
    c = ws.cell(row=i, column=2, value=b)
    c.font, c.alignment = f_norm, Alignment(wrap_text=True, vertical="top")
    if b == "" and a:
        ws.cell(row=i, column=1).fill = fill_head

# ---------------------------------------------------------------- clickup_tarefas
ws = wb.create_sheet("clickup_tarefas")
cols = ["ID", "Fonte", "Nome", "Status", "Responsáveis", "Tags", "Prioridade", "Prazo", "Atualizada em",
        "Concluída em", "Lista", "Filial", "Link", "Coletada em"]
cabecalho(ws, cols, [14, 11, 50, 16, 34, 24, 11, 12, 17, 17, 18, 11, 38, 17])
d = json.loads((RAIZ / "data" / "clickup.json").read_text(encoding="utf-8"))
coleta = datetime.fromisoformat(d["gerado_em"].replace("Z", "+00:00")).replace(tzinfo=None) - timedelta(hours=3)
r = 2
for fonte, bloco in d["fontes"].items():
    for t in bloco["tarefas"]:
        tags = [x["name"] for x in t.get("tags", [])]
        linha = [t["id"], fonte, t["name"], t["status"],
                 ", ".join(a["username"] or "" for a in t.get("assignees", [])), ", ".join(tags),
                 t.get("priority") or "", ms_para_data(t.get("due_date"), False),
                 ms_para_data(t.get("date_updated")), ms_para_data(t.get("date_closed")),
                 (t.get("list") or {}).get("name", ""), filial(fonte, tags), t["url"], coleta]
        for i, v in enumerate(linha, 1):
            c = ws.cell(row=r, column=i, value=v)
            c.font = f_norm
            if i == 8:
                c.number_format = DATA
            elif i in (9, 10, 14):
                c.number_format = DATA + " hh:mm"
        r += 1
ULT_TAR = max(r - 1, 2)
ws.auto_filter.ref = f"A1:N{ULT_TAR}"
N_TAR = 5000  # faixa das fórmulas, com folga para o crescimento diário

# ---------------------------------------------------------------- clickup_historico
ws = wb.create_sheet("clickup_historico")
cabecalho(ws, ["Data da coleta", "ID da tarefa", "Fonte", "Status anterior", "Status novo"], [18, 14, 11, 20, 20])
exemplo(ws, [datetime(2026, 10, 14, 7, 0), "wdrhz35uct", "anuncios", "precificação", "subindo anúncios"], {1: DATA + " hh:mm"})
entrada(ws, "A3:E3000")

# ---------------------------------------------------------------- plano_90_dias
ws = wb.create_sheet("plano_90_dias")
cols = ["Código", "Fase (1 a 3)", "Atividade", "Responsável", "Início", "Prazo", "Status", "% concluído", "Peso",
        "Bloqueio", "Observações", "% considerado", "Situação"]
cabecalho(ws, cols, [10, 11, 46, 20, 12, 12, 16, 13, 8, 28, 36, 14, 12])
exemplo(ws, ["1.1", 1, "Mapear fornecedores prioritários", "Polielly Morato", date(2026, 10, 19), date(2026, 10, 30),
             "Em andamento", 0.4, 2, "", "Exemplo: apague esta linha", None, None],
        {5: DATA, 6: DATA, 8: "0%"})
for rr in range(2, ULT + 1):
    ws.cell(row=rr, column=12, value=f'=IF(C{rr}="","",IF(G{rr}="Concluída",1,N(H{rr})))')
    ws.cell(row=rr, column=13, value=f'=IF(C{rr}="","",IF(G{rr}="Concluída","Concluída",IF(AND(F{rr}<>"",F{rr}<TODAY()),"Atrasada","No prazo")))')
    ws.cell(row=rr, column=12).number_format = "0%"
    for c in (12, 13):
        ws.cell(row=rr, column=c).font = f_norm
entrada(ws, f"A3:K{ULT}")
entrada(ws, f"E3:F{ULT}", DATA)
entrada(ws, f"H3:H{ULT}", "0%")
lista(ws, f"B3:B{ULT}", ["1", "2", "3"])
lista(ws, f"G3:G{ULT}", ["Não iniciada", "Em andamento", "Bloqueada", "Concluída"])

# ---------------------------------------------------------------- posicoes_fornecedor
ws = wb.create_sheet("posicoes_fornecedor")
cabecalho(ws, ["Data da posição", "Fornecedor", "Produtos no catálogo", "Cadastrados no ERP",
               "Disponíveis para venda", "Observação"], [16, 26, 16, 16, 18, 40])
exemplo(ws, [date(2026, 10, 13), "Fornecedor Exemplo", 1200, 800, 650, "Exemplo: apague esta linha"], {1: DATA})
entrada(ws, f"A3:F{ULT}")
entrada(ws, f"A3:A{ULT}", DATA)

# ---------------------------------------------------------------- fornecedores
ws = wb.create_sheet("fornecedores")
cabecalho(ws, ["Fornecedor", "Filial", "Modelo", "Última posição", "Catálogo", "Cadastrados", "Disponíveis",
               "A cadastrar", "Cobertura de cadastro", "Cobertura de venda"], [26, 12, 18, 14, 11, 12, 12, 12, 14, 14])
exemplo(ws, ["Fornecedor Exemplo", "Itajaí", "Cross-docking"])
P = "posicoes_fornecedor"
for rr in range(2, 201):
    m = f"SUMPRODUCT(MAX(({P}!$B$3:$B${ULT}=$A{rr})*{P}!$A$3:$A${ULT}))"
    ws.cell(row=rr, column=4, value=f'=IF($A{rr}="","",IF({m}=0,"",{m}))').number_format = DATA
    for col, orig in ((5, "C"), (6, "D"), (7, "E")):
        ws.cell(row=rr, column=col, value=f'=IF($D{rr}="","",SUMIFS({P}!${orig}$3:${orig}${ULT},{P}!$B$3:$B${ULT},$A{rr},{P}!$A$3:$A${ULT},$D{rr}))')
    ws.cell(row=rr, column=8, value=f'=IF($E{rr}="","",$E{rr}-$F{rr})')
    ws.cell(row=rr, column=9, value=f'=IF(OR($E{rr}="",$E{rr}=0),"",$F{rr}/$E{rr})').number_format = PCT
    ws.cell(row=rr, column=10, value=f'=IF(OR($E{rr}="",$E{rr}=0),"",$G{rr}/$E{rr})').number_format = PCT
    for c in range(4, 11):
        ws.cell(row=rr, column=c).font = f_norm
ws["A3"] = "Vonder"
entrada(ws, "A3:C200")
lista(ws, "B3:B200", ["Itajaí", "Londrina"])
lista(ws, "C3:C200", ["A definir", "Cross-docking", "Dropshipping", "Estoque próprio"])

# ---------------------------------------------------------------- fornecedor_painel
ws = wb.create_sheet("fornecedor_painel")
ws.column_dimensions["A"].width = 30
ws.column_dimensions["B"].width = 28
ws["A1"] = "Expansão por fornecedor"
ws["A1"].font = f_tit
ws["A2"] = "Escolha o fornecedor na célula amarela. Os números vêm da posição mais recente em posicoes_fornecedor."
ws["A2"].font = f_nota
rot = ["Fornecedor", "Filial", "Modelo", "Posição de", "Produtos no catálogo", "Cadastrados no ERP",
       "Disponíveis para venda", "Faltam cadastrar", "Cobertura de cadastro", "Cobertura de venda"]
F = "fornecedores"
busca = lambda col: f'IFERROR(INDEX({F}!${col}$2:${col}$200,MATCH($B$4,{F}!$A$2:$A$200,0))' + ('&""' if col in "BC" else "") + ',"")'
for i, t in enumerate(rot):
    ws.cell(row=4 + i, column=1, value=t).font = Font(name=FONTE, size=10, bold=True)
ws["B4"].fill, ws["B4"].font = fill_in, f_in
dv = DataValidation(type="list", formula1=f"={F}!$A$3:$A$200", allow_blank=True)
ws.add_data_validation(dv)
dv.add("B4")
ws["B4"] = "Vonder"
for i, col in enumerate("BCDEFGHIJ", 5):
    c = ws.cell(row=i, column=2, value=f'=IF($B$4="","",{busca(col)})')
    c.font = f_norm
    c.alignment = Alignment(horizontal="left")
ws["B7"].number_format = DATA
ws["B12"].number_format = PCT
ws["B13"].number_format = PCT
ws["A15"] = "Sem posição registrada, os números ficam em branco: a base para essa cobertura ainda não existe."
ws["A15"].font = f_nota

# ---------------------------------------------------------------- vonder_60
ws = wb.create_sheet("vonder_60")
cabecalho(ws, ["Data da posição", "Anúncios publicados", "Produtos no ERP", "Variação de publicados",
               "Observação"], [16, 18, 16, 18, 40])
exemplo(ws, [date(2026, 10, 13), 150, 400, None, "Exemplo: apague esta linha"], {1: DATA})
for rr in range(3, ULT + 1):
    ws.cell(row=rr, column=4, value=f'=IF(OR(B{rr}="",B{rr-1}="",{rr}=3),"",B{rr}-B{rr-1})').font = f_norm
entrada(ws, f"A3:C{ULT}")
entrada(ws, f"A3:A{ULT}", DATA)
entrada(ws, f"E3:E{ULT}")
ws["G1"], ws["H1"] = "Meta de publicados", None
ws["G2"], ws["H2"] = "Prazo da meta", None
ws["G3"], ws["H3"] = "Publicados hoje", f'=IFERROR(LOOKUP(2,1/(B3:B{ULT}<>""),B3:B{ULT}),"")'
ws["G4"], ws["H4"] = "% da meta", '=IF(OR(H1="",H1=0,H3=""),"",H3/H1)'
ws["G5"], ws["H5"] = "Dias até o prazo", '=IF(H2="","",H2-TODAY())'
for k in ("G1", "G2", "G3", "G4", "G5"):
    ws[k].font = Font(name=FONTE, size=10, bold=True)
for k in ("H1", "H2"):
    ws[k].fill, ws[k].font = fill_in, f_in
ws["H2"].number_format = DATA
ws["H4"].number_format = PCT
for k in ("H3", "H4", "H5"):
    ws[k].font = f_norm
ws.column_dimensions["G"].width = 20
ws.column_dimensions["H"].width = 14

# ---------------------------------------------------------------- lotes
ws = wb.create_sheet("lotes")
cols = ["Lote", "Fornecedor", "Recebido em", "Início do cadastro", "Concluído em", "Cadastrados", "Pendentes",
        "Devolvidos", "Conferência", "Dias de execução", "Recebimento → início (dias)", "Foi devolvido?"]
cabecalho(ws, cols, [12, 24, 13, 15, 14, 13, 11, 11, 14, 13, 16, 13])
exemplo(ws, ["L-001", "Fornecedor Exemplo", date(2026, 10, 5), date(2026, 10, 7), date(2026, 10, 14), 80, 5, 3,
             "Aprovada", None, None, None], {3: DATA, 4: DATA, 5: DATA})
for rr in range(2, ULT + 1):
    ws.cell(row=rr, column=10, value=f'=IF(OR(D{rr}="",E{rr}=""),"",E{rr}-D{rr})')
    ws.cell(row=rr, column=11, value=f'=IF(OR(C{rr}="",D{rr}=""),"",D{rr}-C{rr})')
    ws.cell(row=rr, column=12, value=f'=IF(A{rr}="","",IF(OR(I{rr}="Devolvida",N(H{rr})>0),"Sim","Não"))')
    for c in (10, 11, 12):
        ws.cell(row=rr, column=c).font = f_norm
entrada(ws, f"A3:I{ULT}")
entrada(ws, f"C3:E{ULT}", DATA)
lista(ws, f"I3:I{ULT}", ["Pendente", "Aprovada", "Devolvida"])

# ---------------------------------------------------------------- metas_base
ws = wb.create_sheet("metas_base")
cabecalho(ws, ["Indicador", "Unidade", "Melhor quando", "Valor de base", "Meta planejada", "Prazo da meta",
               "Fonte da base / observação"], [44, 10, 14, 14, 16, 14, 56])
exemplo(ws, ["Exemplo: Cumprimento de prazo", "%", "Maior", 0.7, 0.9, date(2026, 12, 31),
             "Exemplo: apague esta linha. Percentuais em formato 0,9 = 90%"], {4: "0%", 5: "0%", 6: DATA})
ind = [("Cumprimento de prazo", "%", "Maior"), ("Retrabalho (lotes devolvidos)", "%", "Menor"),
       ("Devolução na 1ª conferência", "%", "Menor"), ("Tempo médio de execução do cadastro", "dias", "Menor"),
       ("Espera entre recebimento e início", "dias", "Menor"), ("Plano de 90 dias concluído", "%", "Maior"),
       ("Cobertura média de cadastro dos fornecedores", "%", "Maior"),
       ("Cobertura média de venda dos fornecedores", "%", "Maior"),
       ("Vonder 60: anúncios publicados", "un", "Maior")]
for i, (a, u, m) in enumerate(ind, 3):
    ws.cell(row=i, column=1, value=a).font = f_in
    ws.cell(row=i, column=2, value=u).font = f_in
    ws.cell(row=i, column=3, value=m).font = f_in
    for c in (4, 5, 6, 7):
        ws.cell(row=i, column=c).font = f_in
        ws.cell(row=i, column=c).fill = fill_in
    ws.cell(row=i, column=6).number_format = DATA
    pct = u == "%"
    for c in (4, 5):
        ws.cell(row=i, column=c).number_format = "0.0%" if pct else "0.0"
lista(ws, "C3:C60", ["Maior", "Menor"])

# ---------------------------------------------------------------- relatorios
ws = wb.create_sheet("relatorios")
for col, w in zip("ABCDEF", (44, 14, 16, 16, 18, 50)):
    ws.column_dimensions[col].width = w
ws["A1"] = "Relatórios · planejado × realizado"
ws["A1"].font = f_tit
ws["A2"] = "Base e meta vêm da aba metas_base. Realizado é calculado das demais abas. Sem meta preenchida, o status fica em branco."
ws["A2"].font = f_nota
for i, t in enumerate(["Indicador", "Valor de base", "Meta planejada", "Realizado", "Status", "Como é calculado"], 1):
    c = ws.cell(row=4, column=i, value=t)
    c.font, c.fill = f_head, fill_head
T = "clickup_tarefas"
rt = lambda col: f"{T}!${col}$2:${col}${N_TAR}"
concl = f'({rt("J")}<>"")'
prazo_ok = (f'SUMPRODUCT({concl}*({rt("H")}<>"")*({rt("J")}<{rt("H")}+1))')
prazo_tot = f'SUMPRODUCT({concl}*({rt("H")}<>""))'
L = lambda col: f"lotes!${col}$3:${col}${ULT}"
real = {
    "Cumprimento de prazo": (f'=IF({prazo_tot}=0,"",{prazo_ok}/{prazo_tot})', PCT,
                             "Concluídas com prazo, fechadas até o dia do prazo ÷ concluídas com prazo (clickup_tarefas)"),
    "Retrabalho (lotes devolvidos)": (f'=IF(COUNTA({L("A")})=0,"",COUNTIF({L("L")},"Sim")/COUNTA({L("A")}))', PCT,
                                      "Lotes marcados como devolvidos ÷ lotes registrados (lotes)"),
    "Devolução na 1ª conferência": (f'=IF(COUNTA({L("I")})=0,"",COUNTIF({L("I")},"Devolvida")/COUNTA({L("I")}))', PCT,
                                    "Lotes com conferência Devolvida ÷ lotes com conferência preenchida (lotes)"),
    "Tempo médio de execução do cadastro": (f'=IFERROR(AVERAGE({L("J")}),"")', "0.0",
                                            "Média de dias entre início do cadastro e conclusão (lotes)"),
    "Espera entre recebimento e início": (f'=IFERROR(AVERAGE({L("K")}),"")', "0.0",
                                          "Média de dias entre recebimento e início do cadastro (lotes)"),
    "Plano de 90 dias concluído": ('=IF(SUM(plano_90_dias!$I$3:$I$1000)=0,"",SUMPRODUCT(plano_90_dias!$I$3:$I$1000,plano_90_dias!$L$3:$L$1000)/SUM(plano_90_dias!$I$3:$I$1000))', PCT,
                                   "Média do % de cada atividade ponderada pelo peso (plano_90_dias). Atividade sem peso não entra"),
    "Cobertura média de cadastro dos fornecedores": ('=IFERROR(AVERAGE(fornecedores!$I$3:$I$200),"")', PCT,
                                                     "Média de cadastrados ÷ catálogo nos fornecedores com posição (fornecedores)"),
    "Cobertura média de venda dos fornecedores": ('=IFERROR(AVERAGE(fornecedores!$J$3:$J$200),"")', PCT,
                                                  "Média de disponíveis ÷ catálogo nos fornecedores com posição (fornecedores)"),
    "Vonder 60: anúncios publicados": ('=vonder_60!$H$3', "#,##0", "Posição mais recente em vonder_60"),
}
for i, (nome, _, _) in enumerate(ind):
    rr = 5 + i
    mr = 3 + i  # linha do indicador em metas_base
    ws.cell(row=rr, column=1, value=f"=metas_base!A{mr}")
    ws.cell(row=rr, column=2, value=f'=IF(metas_base!D{mr}="","",metas_base!D{mr})')
    ws.cell(row=rr, column=3, value=f'=IF(metas_base!E{mr}="","",metas_base!E{mr})')
    f, fmt, como = real[nome]
    ws.cell(row=rr, column=4, value=f)
    ws.cell(row=rr, column=5, value=(f'=IF(OR(C{rr}="",D{rr}=""),"",IF(metas_base!C{mr}="Menor",IF(D{rr}<=C{rr},"Dentro da meta","Fora da meta"),'
                                     f'IF(D{rr}>=C{rr},"Dentro da meta","Fora da meta")))'))
    ws.cell(row=rr, column=6, value=como)
    for c in range(1, 7):
        ws.cell(row=rr, column=c).font = f_norm
        ws.cell(row=rr, column=c).border = borda
    ws.cell(row=rr, column=6).font = f_nota
    for c in (2, 3, 4):
        ws.cell(row=rr, column=c).number_format = fmt
ws.freeze_panes = "A5"

# resumo do ClickUp
b = 5 + len(ind) + 2
ws.cell(row=b, column=1, value="Tarefas do ClickUp por fonte").font = Font(name=FONTE, size=11, bold=True)
for i, t in enumerate(["Fonte", "Total", "Abertas", "Concluídas", "Atrasadas (abertas com prazo vencido)"], 1):
    c = ws.cell(row=b + 1, column=i, value=t)
    c.font, c.fill = f_head, fill_head
for i, fonte in enumerate(["anuncios", "compras", "itajai", "londrina"]):
    rr = b + 2 + i
    ws.cell(row=rr, column=1, value=fonte)
    ws.cell(row=rr, column=2, value=f'=COUNTIF({rt("B")},A{rr})')
    ws.cell(row=rr, column=3, value=f'=COUNTIFS({rt("B")},A{rr},{rt("J")},"")')
    ws.cell(row=rr, column=4, value=f'=COUNTIFS({rt("B")},A{rr},{rt("J")},"<>")')
    ws.cell(row=rr, column=5, value=f'=SUMPRODUCT(({rt("B")}=A{rr})*({rt("J")}="")*({rt("H")}<>"")*({rt("H")}<TODAY()))')
    for c in range(1, 6):
        ws.cell(row=rr, column=c).font = f_norm

ordem = ["LEIA-ME", "relatorios", "metas_base", "plano_90_dias", "fornecedor_painel", "fornecedores",
         "posicoes_fornecedor", "vonder_60", "lotes", "clickup_tarefas", "clickup_historico"]
wb._sheets = [wb[n] for n in ordem]
SAIDA.parent.mkdir(exist_ok=True)
wb.save(SAIDA)
print("gravado", SAIDA, "tarefas:", ULT_TAR - 1)
