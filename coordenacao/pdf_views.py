"""Views dos relatórios PDF da Coordenação."""

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import HttpResponse
from django.utils import timezone

from config.decorators import grupos_permitidos
from visitas.models import Visita

from .dashboard_utils import (
    distribuicao,
    formatar_data,
    intervalo,
    nome_utilizador,
    serie_horas_entrada,
)
from .forms import FiltroVisitasForm


GRUPO_COORDENACAO = "UCCI_Coordenacao"

MESES_PORTUGUES = (
    "",
    "Janeiro",
    "Fevereiro",
    "Março",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
)


def _periodo_portugues(inicio, fim):
    mes_inicio = MESES_PORTUGUES[inicio.month]
    mes_fim = MESES_PORTUGUES[fim.month]

    if inicio.year == fim.year and inicio.month == fim.month:
        return f"{mes_inicio} de {inicio.year}"
    if inicio.year == fim.year:
        return f"{mes_inicio} a {mes_fim} de {inicio.year}"
    return (
        f"{mes_inicio} de {inicio.year} a "
        f"{mes_fim} de {fim.year}"
    )


def _duracao_visita(visita):
    if not visita.data_hora_saida:
        return "Em curso"

    segundos = max(
        int(
            (
                visita.data_hora_saida
                - visita.data_hora_entrada
            ).total_seconds()
        ),
        0,
    )
    horas, resto = divmod(segundos, 3600)
    minutos = resto // 60
    return f"{horas:02d}:{minutos:02d}"


@login_required
@grupos_permitidos(GRUPO_COORDENACAO)
def relatorio_visitas_pdf(request):
    formulario, inicio, fim = intervalo(
        request,
        FiltroVisitasForm,
    )
    dados_filtro = (
        formulario.cleaned_data
        if formulario.is_valid()
        else {}
    )

    visitas = Visita.objects.select_related(
        "utente",
        "utente__quarto",
    )
    if dados_filtro.get("piso"):
        visitas = visitas.filter(
            utente__quarto__piso=dados_filtro["piso"]
        )
    if dados_filtro.get("tipo_visitante"):
        visitas = visitas.filter(
            tipo_visitante=dados_filtro["tipo_visitante"]
        )

    periodo = visitas.filter(
        data_hora_entrada__date__range=(inicio, fim)
    )
    total_dias = max((fim - inicio).days + 1, 1)
    total_visitas = periodo.count()
    total_concluidas = periodo.filter(
        data_hora_saida__isnull=False
    ).count()
    total_em_curso = periodo.filter(
        data_hora_saida__isnull=True
    ).count()
    total_utentes = periodo.values(
        "utente_id"
    ).distinct().count()

    _, valores_horas = serie_horas_entrada(
        periodo,
        "data_hora_entrada",
        hora_inicio=6,
        hora_fim=21,
    )
    etiquetas_horas = [
        f"{hora:02d}-{hora + 1:02d}"
        for hora in range(6, 21)
    ]
    medias_horas = [
        round(valor / total_dias, 2)
        for valor in valores_horas
    ]

    tipo_labels, tipo_values = distribuicao(
        periodo,
        "tipo_visitante",
        Visita._meta.get_field(
            "tipo_visitante"
        ).choices,
    )
    por_piso = list(
        periodo.order_by()
        .values("utente__quarto__piso")
        .annotate(total=Count("pk"))
        .order_by("utente__quarto__piso")
    )

    piso_escolhido = dict(
        formulario.fields["piso"].choices
    ).get(dados_filtro.get("piso"), "Todos os pisos")
    visitante_escolhido = dict(
        formulario.fields["tipo_visitante"].choices
    ).get(
        dados_filtro.get("tipo_visitante"),
        "Todos os tipos",
    )

    linhas = []
    for visita in periodo.order_by("data_hora_entrada"):
        quarto = visita.utente.quarto
        linhas.append(
            [
                formatar_data(
                    visita.data_hora_entrada,
                    "d/m/Y H:i",
                ),
                visita.nome_visitante or "-",
                visita.utente.nome,
                str(quarto or "-"),
                visita.get_tipo_visitante_display(),
                (
                    formatar_data(
                        visita.data_hora_saida,
                        "d/m/Y H:i",
                    )
                    if visita.data_hora_saida
                    else "-"
                ),
                _duracao_visita(visita),
            ]
        )

    try:
        from .pdf_utils import (
            AZUL,
            LARANJA,
            VERDE,
            VERMELHO,
            construir_relatorio_visitas_pdf,
        )
    except ImportError:
        return HttpResponse(
            "O ReportLab não está instalado. Execute: pip install reportlab",
            status=503,
            content_type="text/plain; charset=utf-8",
        )

    momento = timezone.localtime()
    dados_pdf = {
        "instituicao": getattr(
            settings,
            "NOME_INSTITUICAO",
            "Santa Casa da Misericórdia do Entroncamento",
        ),
        "titulo": "Relatório de Visitas",
        "periodo": _periodo_portugues(inicio, fim),
        "utilizador": nome_utilizador(request.user),
        "gerado_em": formatar_data(momento, "d/m/Y H:i"),
        "filtros": [
            ("Datas", f"{inicio:%d/%m/%Y} a {fim:%d/%m/%Y}"),
            ("Piso", piso_escolhido),
            ("Visitante", visitante_escolhido),
        ],
        "metricas": [
            ("Visitas", total_visitas),
            ("Média por dia", f"{total_visitas / total_dias:.2f}"),
            ("Concluídas", total_concluidas),
            ("Em curso", total_em_curso),
            ("Utentes visitados", total_utentes),
        ],
        "graficos": [
            {
                "titulo": "Visitas por hora de entrada",
                "etiquetas": etiquetas_horas,
                "valores": valores_horas,
                "cor": AZUL,
            },
            {
                "titulo": (
                    "Média diária de visitas por hora "
                    f"({total_dias} dias de calendário)"
                ),
                "etiquetas": etiquetas_horas,
                "valores": medias_horas,
                "cor": VERDE,
                "decimal": True,
            },
            {
                "titulo": "Visitas por piso",
                "etiquetas": [
                    linha["utente__quarto__piso"] or "Sem piso"
                    for linha in por_piso
                ],
                "valores": [linha["total"] for linha in por_piso],
                "cor": LARANJA,
            },
            {
                "titulo": "Visitas por tipo de visitante",
                "etiquetas": tipo_labels,
                "valores": tipo_values,
                "cor": VERMELHO,
            },
        ],
        "cabecalhos": [
            "Entrada",
            "Visitante",
            "Utente",
            "Piso/quarto",
            "Tipo",
            "Saída",
            "Duração",
        ],
        "linhas": linhas,
    }

    resposta = HttpResponse(content_type="application/pdf")
    resposta["Content-Disposition"] = (
        "inline; filename=\""
        f"relatorio_visitas_{inicio:%Y%m%d}_{fim:%Y%m%d}.pdf"
        "\""
    )
    construir_relatorio_visitas_pdf(
        resposta,
        dados_pdf,
    )
    return resposta
