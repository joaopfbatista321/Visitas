from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import Coalesce, ExtractHour, TruncDate
from django.shortcuts import render
from django.utils import timezone
from django.utils.formats import date_format


CORES = ["#4680ff", "#2ed8b6", "#ffb64d", "#ff5370", "#6f42c1", "#00bcd4"]


def nome_utilizador(utilizador):
    if not utilizador:
        return "—"
    return utilizador.get_full_name() or utilizador.username


def formatar_data(valor, formato="d/m/Y"):
    if not valor:
        return "—"
    if hasattr(valor, "hour") and timezone.is_aware(valor):
        valor = timezone.localtime(valor)
    return date_format(valor, formato)


def escolha(escolhas, valor):
    return dict(escolhas).get(valor, valor or "—")


def intervalo(request, classe_formulario):
    hoje = timezone.localdate()
    inicio_padrao = hoje.replace(day=1)
    dados = request.GET or None
    formulario = classe_formulario(
        dados,
        initial={"data_inicio": inicio_padrao, "data_fim": hoje},
    )
    valido = formulario.is_valid() if dados is not None else False
    if valido:
        periodo_rapido = formulario.cleaned_data.get("periodo_rapido")

        if periodo_rapido == "SEMANA":
            inicio = hoje - timedelta(days=hoje.weekday())
            fim = hoje
        elif periodo_rapido == "MES":
            inicio = hoje.replace(day=1)
            fim = hoje
        elif periodo_rapido == "ANO":
            inicio = hoje.replace(month=1, day=1)
            fim = hoje
        else:
            inicio = formulario.cleaned_data.get("data_inicio") or inicio_padrao
            fim = formulario.cleaned_data.get("data_fim") or hoje
    else:
        inicio = inicio_padrao
        fim = hoje
    return formulario, inicio, fim


def _dias(inicio, fim):
    return [inicio + timedelta(days=i) for i in range((fim - inicio).days + 1)]


def serie_contagem(queryset, campo, inicio, fim):
    linhas = (
        queryset.filter(**{f"{campo}__date__range": (inicio, fim)})
        .annotate(_dia=TruncDate(campo))
        .values("_dia")
        .annotate(total=Count("pk", distinct=True))
        .order_by("_dia")
    )
    mapa = {linha["_dia"]: linha["total"] for linha in linhas}
    eixo = _dias(inicio, fim)
    return [dia.strftime("%d/%m") for dia in eixo], [mapa.get(dia, 0) for dia in eixo]


def serie_data(queryset, campo, inicio, fim):
    linhas = (
        queryset.filter(**{f"{campo}__range": (inicio, fim)})
        .values(campo)
        .annotate(total=Count("pk", distinct=True))
        .order_by(campo)
    )
    mapa = {linha[campo]: linha["total"] for linha in linhas}
    eixo = _dias(inicio, fim)
    return [dia.strftime("%d/%m") for dia in eixo], [mapa.get(dia, 0) for dia in eixo]


def serie_soma(queryset, campo_data, campo_valor, inicio, fim):
    linhas = (
        queryset.filter(**{f"{campo_data}__date__range": (inicio, fim)})
        .annotate(_dia=TruncDate(campo_data))
        .values("_dia")
        .annotate(total=Coalesce(Sum(campo_valor), Decimal("0.00")))
        .order_by("_dia")
    )
    mapa = {linha["_dia"]: float(linha["total"]) for linha in linhas}
    eixo = _dias(inicio, fim)
    return [dia.strftime("%d/%m") for dia in eixo], [mapa.get(dia, 0) for dia in eixo]


def distribuicao(queryset, campo, escolhas):
    contagens = dict(
        queryset.order_by().values_list(campo).annotate(total=Count("pk", distinct=True))
    )
    etiquetas = []
    valores = []
    for valor, nome in escolhas:
        total = contagens.get(valor, 0)
        if total:
            etiquetas.append(nome)
            valores.append(total)
    return etiquetas, valores


def serie_horas_entrada(queryset, campo, hora_inicio=8, hora_fim=21):
    """Conta entradas em intervalos horários, respeitando o fuso horário ativo."""
    linhas = (
        queryset.annotate(
            _hora=ExtractHour(
                campo,
                tzinfo=timezone.get_current_timezone(),
            )
        )
        .filter(_hora__gte=hora_inicio, _hora__lt=hora_fim)
        .order_by()
        .values("_hora")
        .annotate(total=Count("pk", distinct=True))
        .order_by("_hora")
    )
    mapa = {int(linha["_hora"]): linha["total"] for linha in linhas}
    horas = range(hora_inicio, hora_fim)
    etiquetas = [f"{hora:02d}:00–{hora + 1:02d}:00" for hora in horas]
    valores = [mapa.get(hora, 0) for hora in horas]
    return etiquetas, valores


def grafico_area(identificador, titulo, etiquetas, series, coluna="col-xl-8"):
    return {
        "id": identificador,
        "titulo": titulo,
        "coluna": coluna,
        "opcoes": {
            "chart": {"type": "area", "height": 320, "toolbar": {"show": False}},
            "series": series,
            "xaxis": {"categories": etiquetas, "tickAmount": min(len(etiquetas), 12)},
            "stroke": {"curve": "smooth", "width": 3},
            "dataLabels": {"enabled": False},
            "colors": CORES[: len(series)],
            "fill": {
                "type": "gradient",
                "gradient": {"shadeIntensity": 1, "opacityFrom": 0.35, "opacityTo": 0.05},
            },
            "legend": {"position": "top"},
            "noData": {"text": "Sem dados no período"},
        },
    }


def grafico_donut(identificador, titulo, etiquetas, valores, coluna="col-xl-4"):
    return {
        "id": identificador,
        "titulo": titulo,
        "coluna": coluna,
        "opcoes": {
            "chart": {"type": "donut", "height": 320},
            "labels": etiquetas,
            "series": valores,
            "colors": CORES,
            "legend": {"position": "bottom"},
            "dataLabels": {"enabled": True},
            "noData": {"text": "Sem dados no período"},
        },
    }


def grafico_barras(
    identificador,
    titulo,
    etiquetas,
    valores,
    coluna="col-xl-6",
    mostrar_valores=False,
):
    return {
        "id": identificador,
        "titulo": titulo,
        "coluna": coluna,
        "opcoes": {
            "chart": {"type": "bar", "height": 320, "toolbar": {"show": False}},
            "series": [{"name": titulo, "data": valores}],
            "xaxis": {
                "categories": etiquetas,
                "labels": {
                    "rotate": -45 if mostrar_valores else 0,
                    "hideOverlappingLabels": not mostrar_valores,
                    "trim": False,
                },
            },
            "yaxis": {"min": 0, "forceNiceScale": True},
            "grid": {"padding": {"top": 20 if mostrar_valores else 0}},
            "plotOptions": {
                "bar": {
                    "borderRadius": 5,
                    "horizontal": False,
                    "columnWidth": "58%",
                    "dataLabels": {"position": "top"},
                }
            },
            "dataLabels": {
                "enabled": mostrar_valores,
                "offsetY": -18,
                "style": {
                    "fontSize": "12px",
                    "fontWeight": 600,
                    "colors": ["#344054"],
                },
            },
            "colors": [CORES[0]],
            "noData": {"text": "Sem dados no período"},
        },
    }


def metrica(titulo, valor, icone, cor, detalhe=""):
    return {"titulo": titulo, "valor": valor, "icone": icone, "cor": cor, "detalhe": detalhe}


def pagina(titulo, descricao, icone, cor):
    return {"titulo": titulo, "descricao": descricao, "icone": icone, "cor": cor}


def render_dashboard(
    request,
    *,
    pagina,
    formulario,
    inicio,
    fim,
    metricas,
    graficos,
    tabela=None,
    alertas=None,
):
    return render(
        request,
        "coordenacao/dashboard.html",
        {
            "pagina": pagina,
            "filtro": formulario,
            "inicio": inicio,
            "fim": fim,
            "metricas": metricas,
            "graficos": graficos,
            "tabela": tabela,
            "alertas": alertas or [],
            "limpar_url": request.path,
            "atualizado_em": timezone.localtime(),
        },
    )
