"""
Monta e atualiza a planilha excel/Analise_Infra_Tec.xlsx a partir da camada gold.

A planilha tem:
  - Base_Rede_Ano: tabela do Excel (tbRedeAno) com o data mart rede x ano
  - Painel: seletores de ano e rede (validação de dados), indicadores com
    ÍNDICE+CORRESP/SOMASES/MÉDIASES, grade rede x ano com escala de cores e gráfico de linhas
  - Dinamica: tabela dinâmica (índice médio por rede e ano), atualizada ao abrir
  - Leia-me

Chamado pelo pipeline (run_pipeline.py) ao final de cada execução.
"""
from __future__ import annotations

import csv
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.chart import LineChart, Reference
from openpyxl.formatting.rule import ColorScaleRule, CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.formula import ArrayFormula
from openpyxl.worksheet.table import Table, TableStyleInfo

RAIZ = Path(__file__).resolve().parents[1]
GOLD = RAIZ / "dados" / "gold"
ARQUIVO = RAIZ / "excel" / "Analise_Infra_Tec.xlsx"

NAVY, VERDE, CORAL, CINZA = "1D3557", "2A9D8F", "E76F51", "667085"
COR_REDE = {"Municipal": "2A9D8F", "Estadual": "3D5A80", "Federal": "E9C46A", "Privada": "E76F51"}
COLUNAS = [
    ("ano", "Ano", "0"), ("rede", "Rede", "@"), ("grupo_rede", "Grupo", "@"), ("ordem_rede", "Ordem", "0"),
    ("escolas", "Escolas", "#,##0"), ("matriculas", "Matrículas", "#,##0"),
    ("pct_internet", "% internet", "0.0%"), ("pct_banda_larga", "% banda larga", "0.0%"),
    ("pct_internet_alunos", "% internet alunos", "0.0%"), ("pct_internet_aprendizagem", "% internet ensino", "0.0%"),
    ("pct_laboratorio", "% laboratório", "0.0%"), ("pct_computador_aluno", "% computador alunos", "0.0%"),
    ("pct_rede_sem_fio", "% rede sem fio", "0.0%"), ("computadores_alunos", "Computadores alunos", "#,##0"),
    ("indice_infra_tec", "Índice", "0.0"), ("alunos_por_computador", "Alunos por computador", "0.0"),
    ("delta_indice_ano_anterior", "Var. índice ano anterior", "+0.0;-0.0;0.0"),
    ("delta_pct_internet_ano_anterior", "Var. % internet ano anterior", "+0.0%;-0.0%;0.0%"),
    ("delta_indice_desde_inicio", "Var. índice desde o início", "+0.0;-0.0;0.0"),
    ("posicao_no_ano", "Posição no ano", "0"),
]
TITULO = Font(name="Calibri", size=16, bold=True, color="FFFFFF")
FAIXA = PatternFill("solid", fgColor=NAVY)
CAB = Font(bold=True, color="FFFFFF")
CAB_FILL = PatternFill("solid", fgColor=VERDE)
FINA = Side(style="thin", color="E4E7EC")


def ler_mart() -> list[dict]:
    with open(GOLD / "mart_rede_ano.csv", encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    def num(v):
        if v in ("", None):
            return None
        x = float(v)
        return int(x) if x.is_integer() and "." not in v else x
    return sorted(([{k: (v if k in ("rede", "grupo_rede") else num(v)) for k, v in l.items()} for l in linhas]),
                  key=lambda r: (r["ano"], r["ordem_rede"]))


def ler_metadados() -> dict:
    with open(GOLD / "metadados.csv", encoding="utf-8") as f:
        return next(csv.DictReader(f))


def escrever_base(ws, dados):
    ws.delete_rows(1, ws.max_row + 1)
    for t in list(ws.tables):
        del ws.tables[t]
    ws.append([c[1] for c in COLUNAS])
    for r in dados:
        ws.append([r.get(c[0]) for c in COLUNAS])
    for j, (_, _, fmt) in enumerate(COLUNAS, start=1):
        for i in range(2, len(dados) + 2):
            ws.cell(i, j).number_format = fmt
        ws.column_dimensions[get_column_letter(j)].width = max(10, len(COLUNAS[j - 1][1]) + 3)
    ref = f"A1:{get_column_letter(len(COLUNAS))}{len(dados) + 1}"
    tab = Table(displayName="tbRedeAno", ref=ref)
    tab.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
    ws.add_table(tab)
    ws.freeze_panes = "C2"
    return ref


def montar_painel(wb, dados, meta):
    if "Painel" in wb.sheetnames:
        del wb["Painel"]
    ws = wb.create_sheet("Painel", 0)
    ws.sheet_view.showGridLines = False
    anos = sorted({r["ano"] for r in dados})
    redes = [r for r in ["Municipal", "Estadual", "Federal", "Privada"] if any(d["rede"] == r for d in dados)]

    ws.merge_cells("B2:K2")
    ws["B2"] = "Infraestrutura tecnológica das escolas · análise por rede e ano"
    ws["B2"].font, ws["B2"].fill = TITULO, FAIXA
    ws.row_dimensions[2].height = 30
    ws["B3"] = f"Fonte: {meta['fonte']} | {meta['uf']}, {meta['anos']}"
    ws["B3"].font = Font(italic=True, color=CORAL if meta.get("eh_amostra") == "1" else CINZA, size=9)

    # ---------- seletores (validação de dados)
    ws["B5"], ws["B6"] = "Ano", "Rede"
    ws["C5"], ws["C6"] = anos[-1], "Municipal"
    for c in ("B5", "B6"):
        ws[c].font = Font(bold=True)
    for c in ("C5", "C6"):
        ws[c].fill = PatternFill("solid", fgColor="E0F2F1")
        ws[c].border = Border(FINA, FINA, FINA, FINA)
    dv_ano = DataValidation(type="list", formula1='"' + ",".join(str(a) for a in anos) + '"', allow_blank=False)
    dv_rede = DataValidation(type="list", formula1='"' + ",".join(redes) + '"', allow_blank=False)
    ws.add_data_validation(dv_ano)
    ws.add_data_validation(dv_rede)
    dv_ano.add("C5")
    dv_rede.add("C6")
    ws["D5"] = "← escolha o ano e a rede"
    ws["D5"].font = Font(color=CINZA, italic=True, size=9)

    # ---------- indicadores com fórmulas
    ws["B8"] = "Indicador"
    ws["C8"] = "Valor"
    ws["D8"] = "Fórmula usada"
    for c in ("B8", "C8", "D8"):
        ws[c].font, ws[c].fill = CAB, CAB_FILL
    ind = [
        ("Índice de infraestrutura (0 a 100)",
         '=INDEX(tbRedeAno[Índice],MATCH(1,(tbRedeAno[Ano]=$C$5)*(tbRedeAno[Rede]=$C$6),0))', "0.0",
         "ÍNDICE + CORRESP com dois critérios (fórmula de matriz)"),
        ("% de escolas com internet",
         '=SUMIFS(tbRedeAno[% internet],tbRedeAno[Ano],$C$5,tbRedeAno[Rede],$C$6)', "0.0%", "SOMASES"),
        ("Escolas", '=SUMIFS(tbRedeAno[Escolas],tbRedeAno[Ano],$C$5,tbRedeAno[Rede],$C$6)', "#,##0", "SOMASES"),
        ("Variação do índice vs ano anterior",
         '=IFERROR(C9-SUMIFS(tbRedeAno[Índice],tbRedeAno[Ano],$C$5-1,tbRedeAno[Rede],$C$6),"")', "+0.0;-0.0;0.0",
         "SOMASES com o ano anterior"),
        ("Índice médio de todas as redes no ano",
         '=AVERAGEIFS(tbRedeAno[Índice],tbRedeAno[Ano],$C$5)', "0.0", "MÉDIASES (média simples das redes)"),
        ("Posição da rede no ano", '=COUNTIFS(tbRedeAno[Ano],$C$5,tbRedeAno[Índice],">"&C9)+1', "0",
         "CONT.SES"),
        ("Melhor rede no ano",
         '=INDEX(tbRedeAno[Rede],MATCH(1,(tbRedeAno[Ano]=$C$5)*(tbRedeAno[Posição no ano]=1),0))', "@",
         "ÍNDICE + CORRESP sobre a coluna de ranking (RANK do SQL)"),
    ]
    for i, (rot, form, fmt, expl) in enumerate(ind, start=9):
        ws.cell(i, 2, rot)
        celula = f"C{i}"
        # fórmulas com critério matricial (A=B)*(C=D) são gravadas como fórmula de matriz
        ws.cell(i, 3, ArrayFormula(celula, form) if "*(" in form else form).number_format = fmt
        ws.cell(i, 3).font = Font(bold=True, color=NAVY, size=12)
        ws.cell(i, 4, expl).font = Font(color=CINZA, size=9)
        for j in (2, 3, 4):
            ws.cell(i, j).border = Border(bottom=FINA)
    ws.conditional_formatting.add("C12", CellIsRule(operator="lessThan", formula=["0"], font=Font(color=CORAL, bold=True)))
    ws.conditional_formatting.add("C12", CellIsRule(operator="greaterThan", formula=["0"], font=Font(color=VERDE, bold=True)))

    # ---------- grade rede x ano (fórmulas) + escala de cores + gráfico
    lin0 = 18
    ws.cell(lin0 - 1, 2, "Índice de infraestrutura tecnológica por rede e ano").font = Font(bold=True, size=12, color=NAVY)
    ws.cell(lin0, 2, "Ano").font = CAB
    ws.cell(lin0, 2).fill = CAB_FILL
    for j, rede in enumerate(redes, start=3):
        c = ws.cell(lin0, j, rede)
        c.font, c.fill = CAB, PatternFill("solid", fgColor=COR_REDE[rede])
    for i, ano in enumerate(anos, start=lin0 + 1):
        ws.cell(i, 2, ano)
        for j, rede in enumerate(redes, start=3):
            col = get_column_letter(j)
            ws.cell(i, j, f'=IFERROR(AVERAGEIFS(tbRedeAno[Índice],tbRedeAno[Ano],$B{i},tbRedeAno[Rede],{col}${lin0}),"")'
                    ).number_format = "0.0"
    fim = lin0 + len(anos)
    ultima_col = get_column_letter(2 + len(redes))
    ws.conditional_formatting.add(f"C{lin0 + 1}:{ultima_col}{fim}",
                                  ColorScaleRule(start_type="min", start_color="FDECE7", mid_type="percentile",
                                                 mid_value=50, mid_color="F1F7F6", end_type="max", end_color="7CC4BA"))
    graf = LineChart()
    graf.title = "Índice por rede"
    graf.height, graf.width = 8, 16
    graf.y_axis.title = "Índice (0 a 100)"
    dados_ref = Reference(ws, min_col=3, max_col=2 + len(redes), min_row=lin0, max_row=fim)
    graf.add_data(dados_ref, titles_from_data=True)
    graf.set_categories(Reference(ws, min_col=2, min_row=lin0 + 1, max_row=fim))
    for serie, rede in zip(graf.series, redes):
        serie.graphicalProperties.line.solidFill = COR_REDE[rede]
        serie.graphicalProperties.line.width = 28000
        serie.smooth = False
    ws.add_chart(graf, f"F5")
    for col, w in {"A": 2, "B": 38, "C": 14, "D": 30, "E": 14, "F": 12}.items():
        ws.column_dimensions[col].width = w


def montar_leiame(wb, meta):
    if "Leia-me" in wb.sheetnames:
        del wb["Leia-me"]
    ws = wb.create_sheet("Leia-me")
    ws.sheet_view.showGridLines = False
    textos = [
        ("Infraestrutura tecnológica das escolas", True),
        ("Pergunta: como a infraestrutura tecnológica mudou ao longo dos anos, comparando rede municipal, estadual e privada?", False),
        ("", False),
        (f"Fonte: {meta['fonte']}", False),
        (f"UF: {meta['uf']} | Anos: {meta['anos']}", False),
        ("", False),
        ("Abas", True),
        ("Painel: escolha ano e rede (listas suspensas) para ver os indicadores calculados com ÍNDICE + CORRESP, SOMASES, MÉDIASES e CONT.SES.", False),
        ("Dinamica: tabela dinâmica com o índice médio por rede e ano. Ela é atualizada ao abrir o arquivo.", False),
        ("Base_Rede_Ano: tabela tbRedeAno, gerada pela camada gold do pipeline (SQL).", False),
        ("", False),
        ("Para atualizar: rode  python pipeline/run_pipeline.py  e abra este arquivo de novo.", False),
    ]
    for i, (t, negrito) in enumerate(textos, start=2):
        c = ws.cell(i, 2, t)
        c.font = Font(bold=negrito, size=14 if i == 2 else 11, color=NAVY if negrito else "1D2939")
        c.alignment = Alignment(wrap_text=False)
    ws.column_dimensions["B"].width = 120


def sem_datas(wb) -> None:
    wb.properties.creator = "Gustavo Oliveira"
    wb.properties.lastModifiedBy = "Gustavo Oliveira"


def remover_datas_do_arquivo(caminho: Path) -> None:
    """Tira do .xlsx as datas de criação e modificação (docProps/core.xml)."""
    import re
    import shutil
    import zipfile
    tmp = caminho.with_suffix(".tmp")
    with zipfile.ZipFile(caminho) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            dados = zin.read(item.filename)
            if item.filename == "docProps/core.xml":
                texto = dados.decode("utf-8")
                texto = re.sub(r"<dcterms:(created|modified)[^>]*>.*?</dcterms:\1>", "", texto)
                texto = re.sub(r"<cp:lastPrinted>.*?</cp:lastPrinted>", "", texto)
                dados = texto.encode("utf-8")
            item.date_time = (1980, 1, 1, 0, 0, 0)
            zout.writestr(item, dados)
    shutil.move(tmp, caminho)


def criar_base_inicial(destino: Path = ARQUIVO) -> None:
    """Usado uma vez para criar o arquivo antes de inserir a tabela dinâmica."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Base_Rede_Ano"
    escrever_base(ws, ler_mart())
    wb.save(destino)


def atualizar() -> None:
    dados, meta = ler_mart(), ler_metadados()
    wb = load_workbook(ARQUIVO)
    ref = escrever_base(wb["Base_Rede_Ano"], dados)
    for ws in wb.worksheets:
        for piv in getattr(ws, "_pivots", []):
            src = piv.cache.cacheSource.worksheetSource
            if src is not None:
                src.ref = ref
                src.sheet = "Base_Rede_Ano"
            piv.cache.refreshOnLoad = True
    montar_painel(wb, dados, meta)
    montar_leiame(wb, meta)
    ordem = ["Painel", "Dinamica", "Base_Rede_Ano", "Leia-me"]
    wb._sheets.sort(key=lambda s: ordem.index(s.title) if s.title in ordem else 99)
    wb.active = 0
    sem_datas(wb)
    # grava num arquivo temporário e só substitui o original se tudo der certo
    novo = ARQUIVO.with_name(ARQUIVO.stem + "_novo.xlsx")
    wb.save(novo)
    remover_datas_do_arquivo(novo)
    novo.replace(ARQUIVO)
    print(f"Excel atualizado: {ARQUIVO.name}")


if __name__ == "__main__":
    atualizar()
