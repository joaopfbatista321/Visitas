"""Construção dos relatórios PDF da Coordenação com ReportLab."""

from html import escape
from math import ceil

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    LongTable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


AZUL = HexColor("#4680ff")
VERDE = HexColor("#2ed8b6")
LARANJA = HexColor("#ffb64d")
VERMELHO = HexColor("#ff5370")
AZUL_ESCURO = HexColor("#1f3a5f")
CINZA_TEXTO = HexColor("#5f6b7a")
CINZA_CLARO = HexColor("#f3f6f9")
CINZA_LINHA = HexColor("#d9e2ec")


def _paragrafo(valor, estilo):
    texto = "" if valor is None else str(valor)
    return Paragraph(escape(texto), estilo)


def _passo_eixo(maximo, decimal=False):
    if maximo <= 0:
        return 0.2 if decimal else 1

    bruto = maximo / 5
    if decimal:
        return max(round(bruto, 2), 0.1)
    return max(ceil(bruto), 1)


def grafico_barras_pdf(
    titulo,
    etiquetas,
    valores,
    *,
    cor=AZUL,
    decimal=False,
    largura=760,
    altura=220,
):
    """Cria um gráfico de barras vetorial adequado a A4 horizontal."""
    valores_numericos = [float(valor or 0) for valor in valores]
    if not valores_numericos:
        valores_numericos = [0]
        etiquetas = ["Sem dados"]

    desenho = Drawing(largura, altura)
    desenho.add(
        String(
            largura / 2,
            altura - 15,
            titulo,
            textAnchor="middle",
            fontName="Helvetica-Bold",
            fontSize=11,
            fillColor=AZUL_ESCURO,
        )
    )

    grafico = VerticalBarChart()
    grafico.x = 45
    grafico.y = 42
    grafico.width = largura - 70
    grafico.height = altura - 82
    grafico.data = [valores_numericos]
    grafico.categoryAxis.categoryNames = [str(valor) for valor in etiquetas]
    grafico.categoryAxis.labels.fontName = "Helvetica"
    grafico.categoryAxis.labels.fontSize = 6.5 if len(etiquetas) > 10 else 7.5
    grafico.categoryAxis.labels.angle = 35 if len(etiquetas) > 10 else 0
    grafico.categoryAxis.labels.dy = -13 if len(etiquetas) > 10 else -8
    grafico.categoryAxis.labels.dx = -3 if len(etiquetas) > 10 else 0
    grafico.categoryAxis.strokeColor = CINZA_LINHA
    grafico.valueAxis.valueMin = 0

    maximo = max(valores_numericos)
    passo = _passo_eixo(maximo, decimal=decimal)
    grafico.valueAxis.valueStep = passo
    grafico.valueAxis.valueMax = max(passo * 5, maximo + passo)
    grafico.valueAxis.labels.fontName = "Helvetica"
    grafico.valueAxis.labels.fontSize = 7
    grafico.valueAxis.strokeColor = CINZA_LINHA
    grafico.valueAxis.gridStrokeColor = CINZA_LINHA
    grafico.valueAxis.visibleGrid = True
    grafico.bars[0].fillColor = cor
    grafico.bars[0].strokeColor = cor
    grafico.barSpacing = 3
    grafico.barLabelFormat = "%.2f" if decimal else "%.0f"
    grafico.barLabels.fontName = "Helvetica-Bold"
    grafico.barLabels.fontSize = 6.5
    grafico.barLabels.fillColor = AZUL_ESCURO
    grafico.barLabels.nudge = 6
    desenho.add(grafico)
    return desenho


def _estilos():
    estilos = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle(
            "RelatorioTitulo",
            parent=estilos["Title"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=AZUL_ESCURO,
            alignment=TA_LEFT,
            spaceAfter=3 * mm,
        ),
        "subtitulo": ParagraphStyle(
            "RelatorioSubtitulo",
            parent=estilos["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=CINZA_TEXTO,
            spaceAfter=3 * mm,
        ),
        "secao": ParagraphStyle(
            "RelatorioSecao",
            parent=estilos["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=14,
            textColor=AZUL_ESCURO,
            spaceBefore=2 * mm,
            spaceAfter=2 * mm,
        ),
        "normal": ParagraphStyle(
            "RelatorioNormal",
            parent=estilos["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.black,
        ),
        "pequeno": ParagraphStyle(
            "RelatorioPequeno",
            parent=estilos["Normal"],
            fontName="Helvetica",
            fontSize=6.5,
            leading=8,
            textColor=colors.black,
        ),
        "kpi_titulo": ParagraphStyle(
            "RelatorioKpiTitulo",
            parent=estilos["Normal"],
            fontName="Helvetica",
            fontSize=7,
            leading=8,
            textColor=CINZA_TEXTO,
            alignment=TA_CENTER,
        ),
        "kpi_valor": ParagraphStyle(
            "RelatorioKpiValor",
            parent=estilos["Normal"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            textColor=AZUL_ESCURO,
            alignment=TA_CENTER,
        ),
    }


def construir_relatorio_visitas_pdf(destino, dados):
    """Escreve o relatório de visitas no objeto de destino recebido."""
    estilos = _estilos()
    pagina = landscape(A4)
    documento = SimpleDocTemplate(
        destino,
        pagesize=pagina,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=16 * mm,
        bottomMargin=14 * mm,
        title=dados["titulo"],
        author=dados["utilizador"],
        subject=dados["periodo"],
    )

    def cabecalho_rodape(canvas, doc):
        canvas.saveState()
        largura, altura = pagina
        canvas.setStrokeColor(CINZA_LINHA)
        canvas.setLineWidth(0.5)
        canvas.line(12 * mm, altura - 10 * mm, largura - 12 * mm, altura - 10 * mm)
        canvas.setFont("Helvetica-Bold", 7)
        canvas.setFillColor(AZUL_ESCURO)
        canvas.drawString(12 * mm, altura - 8 * mm, dados["instituicao"])
        canvas.setFont("Helvetica", 6.5)
        canvas.setFillColor(CINZA_TEXTO)
        canvas.drawRightString(
            largura - 12 * mm,
            7 * mm,
            f"Gerado em {dados['gerado_em']} | Página {doc.page}",
        )
        canvas.restoreState()

    historia = [
        _paragrafo(dados["titulo"], estilos["titulo"]),
        _paragrafo(
            f"Período: {dados['periodo']} | Gerado por: {dados['utilizador']}",
            estilos["subtitulo"],
        ),
    ]

    filtros = dados.get("filtros", [])
    if filtros:
        filtro_linha = [
            _paragrafo(f"{titulo}: {valor}", estilos["normal"])
            for titulo, valor in filtros
        ]
        tabela_filtros = Table(
            [filtro_linha],
            colWidths=[documento.width / len(filtro_linha)] * len(filtro_linha),
        )
        tabela_filtros.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), CINZA_CLARO),
                    ("BOX", (0, 0), (-1, -1), 0.5, CINZA_LINHA),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, CINZA_LINHA),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        historia.extend([tabela_filtros, Spacer(1, 4 * mm)])

    metricas = dados.get("metricas", [])
    if metricas:
        tabela_metricas = Table(
            [
                [_paragrafo(titulo, estilos["kpi_titulo"]) for titulo, _ in metricas],
                [_paragrafo(valor, estilos["kpi_valor"]) for _, valor in metricas],
            ],
            colWidths=[documento.width / len(metricas)] * len(metricas),
        )
        tabela_metricas.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                    ("BOX", (0, 0), (-1, -1), 0.5, CINZA_LINHA),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, CINZA_LINHA),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, 0), 6),
                    ("BOTTOMPADDING", (0, 1), (-1, 1), 7),
                ]
            )
        )
        historia.extend([tabela_metricas, Spacer(1, 3 * mm)])

    graficos = dados.get("graficos", [])
    for indice, configuracao in enumerate(graficos):
        if indice > 0:
            historia.append(PageBreak())
        historia.append(
            grafico_barras_pdf(
                configuracao["titulo"],
                configuracao["etiquetas"],
                configuracao["valores"],
                cor=configuracao.get("cor", AZUL),
                decimal=configuracao.get("decimal", False),
                largura=760,
                altura=220,
            )
        )
        historia.append(Spacer(1, 2 * mm))

    historia.extend(
        [
            PageBreak(),
            _paragrafo("Listagem detalhada", estilos["secao"]),
        ]
    )
    cabecalhos = dados.get("cabecalhos", [])
    linhas = dados.get("linhas", [])
    tabela_dados = [
        [_paragrafo(valor, estilos["pequeno"]) for valor in cabecalhos]
    ]
    tabela_dados.extend(
        [_paragrafo(valor, estilos["pequeno"]) for valor in linha]
        for linha in linhas
    )
    if not linhas:
        tabela_dados.append(
            [_paragrafo("Sem visitas no período selecionado.", estilos["pequeno"])]
            + [""] * max(len(cabecalhos) - 1, 0)
        )

    larguras = [24 * mm, 42 * mm, 43 * mm, 28 * mm, 35 * mm, 24 * mm, 20 * mm]
    tabela = LongTable(
        tabela_dados,
        repeatRows=1,
        colWidths=larguras[: len(cabecalhos)],
        hAlign="LEFT",
    )
    tabela.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), AZUL_ESCURO),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.3, CINZA_LINHA),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, CINZA_CLARO]),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    historia.append(tabela)
    documento.build(
        historia,
        onFirstPage=cabecalho_rodape,
        onLaterPages=cabecalho_rodape,
    )
