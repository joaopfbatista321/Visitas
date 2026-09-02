from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, IntegerField
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils import timezone

from cozinha.models import (
    EstadoPedidoCozinha,
    LinhaProdutoPedido,
    LinhaRefeicaoPedido,
    PedidoCozinha,
    TipoPedidoCozinha,
)
from config.decorators import grupos_permitidos
from enfermagem.models import (
    EstadoNotificacaoInstitucional,
    GravidadeQueda,
    RegistoEnfermagem,
    RegistoQueda,
)
from fisioterapia.models import (
    EstadoParticipacaoFisioterapia,
    EstadoSessaoFisioterapia,
    ParticipacaoFisioterapia,
    RegistoFisioterapia,
    SessaoFisioterapia,
)
from visitas.models import (
    EstadoPedidoTransporte,
    EstadoTransporte,
    Externo,
    Isolamento,
    MeioTransporte,
    MovimentoFinanceiro,
    PedidoTransporte,
    Transporte,
    Utente,
    Visita,
)

from .dashboard_utils import (
    distribuicao,
    escolha,
    formatar_data,
    grafico_area,
    grafico_barras,
    grafico_donut,
    intervalo,
    metrica,
    nome_utilizador,
    pagina,
    render_dashboard,
    serie_contagem,
    serie_data,
    serie_horas_entrada,
    serie_soma,
)
from .forms import (
    FiltroCozinhaForm,
    FiltroEnfermagemForm,
    FiltroFinanceiroForm,
    FiltroFisioterapiaForm,
    FiltroPeriodoForm,
    FiltroTransportesForm,
    FiltroUtentesForm,
    FiltroVisitasForm,
)


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


@login_required
@grupos_permitidos(GRUPO_COORDENACAO)
def dashboard_geral(request):
    formulario, inicio, fim = intervalo(request, FiltroPeriodoForm)

    utentes = Utente.objects.all()
    visitas = Visita.objects.all()
    transportes = Transporte.objects.all()
    quedas = RegistoQueda.objects.all()
    sessoes = SessaoFisioterapia.objects.all()
    movimentos = MovimentoFinanceiro.objects.all()
    visitas_periodo = visitas.filter(data_hora_entrada__date__range=(inicio, fim))
    transportes_periodo = transportes.filter(data_hora_saida__date__range=(inicio, fim))
    quedas_periodo = quedas.filter(data_hora_queda__date__range=(inicio, fim))
    sessoes_periodo = sessoes.filter(inicio__date__range=(inicio, fim))
    cozinha_periodo = PedidoCozinha.objects.filter(data_servico__range=(inicio, fim))
    movimentos_periodo = movimentos.filter(data__date__range=(inicio, fim))
    total_entradas = movimentos_periodo.filter(tipo=MovimentoFinanceiro.ENTRADA).aggregate(
        total=Coalesce(Sum("valor"), Decimal("0.00"))
    )["total"]
    total_saidas = movimentos_periodo.filter(tipo=MovimentoFinanceiro.SAIDA).aggregate(
        total=Coalesce(Sum("valor"), Decimal("0.00"))
    )["total"]

    etiquetas, entradas = serie_data(utentes, "data_entrada", inicio, fim)
    _, altas = serie_data(utentes, "data_saida", inicio, fim)
    _, visitas_dia = serie_contagem(visitas, "data_hora_entrada", inicio, fim)

    proximas_altas = utentes.filter(
        data_saida__isnull=True,
        data_prevista_saida__isnull=False,
        data_prevista_saida__gte=timezone.localdate(),
    ).select_related("quarto").order_by("data_prevista_saida", "nome")[:10]
    linhas = [
        {
            "celulas": [
                item.nome,
                item.numero_processo,
                str(item.quarto or "—"),
                formatar_data(item.data_prevista_saida),
            ],
            "url": reverse("visitas:detalhe_utente", args=[item.pk]),
        }
        for item in proximas_altas
    ]

    return render_dashboard(
        request,
        pagina=pagina(
            "Visão geral da UCCI",
            "Indicadores operacionais e clínicos consolidados para a Coordenação.",
            "bar-chart-2",
            "primary",
        ),
        formulario=formulario,
        inicio=inicio,
        fim=fim,
        metricas=[
            metrica("Utentes ativos", utentes.filter(data_saida__isnull=True).count(), "users", "primary"),
            metrica("Visitas", visitas_periodo.count(), "user-check", "success", "no período"),
            metrica("Transportes", transportes_periodo.count(), "truck", "info", "no período"),
            metrica("Quedas", quedas_periodo.count(), "alert-triangle", "danger", "no período"),
            metrica("Sessões de Fisioterapia", sessoes_periodo.count(), "activity", "warning", "no período"),
            metrica("Pedidos da Cozinha", cozinha_periodo.count(), "coffee", "secondary", "no período"),
            metrica("Saldo de movimentos", f"{float(total_entradas - total_saidas):.2f} €", "credit-card", "success"),
        ],
        graficos=[
            grafico_area(
                "atividade-geral",
                "Atividade diária",
                etiquetas,
                [
                    {"name": "Entradas de utentes", "data": entradas},
                    {"name": "Altas", "data": altas},
                    {"name": "Visitas", "data": visitas_dia},
                ],
            ),
            grafico_donut(
                "mix-geral",
                "Volume por área",
                ["Visitas", "Transportes", "Quedas", "Fisioterapia", "Cozinha"],
                [
                    visitas_periodo.count(),
                    transportes_periodo.count(),
                    quedas_periodo.count(),
                    sessoes_periodo.count(),
                    cozinha_periodo.count(),
                ],
            ),
        ],
        tabela={
            "titulo": "Próximas altas previstas",
            "cabecalhos": ["Utente", "Processo", "Quarto", "Data prevista"],
            "linhas": linhas,
            "vazio": "Não existem altas previstas.",
        },
        alertas=[
            {
                "titulo": "Pedidos de transporte por validar",
                "valor": PedidoTransporte.objects.filter(estado=EstadoPedidoTransporte.POR_VALIDAR).count(),
                "cor": "warning",
                "icone": "truck",
            },
            {
                "titulo": "Transportes pendentes",
                "valor": transportes.filter(estado=EstadoTransporte.PENDENTE).count(),
                "cor": "primary",
                "icone": "clock",
            },
            {
                "titulo": "Notificações de queda pendentes",
                "valor": quedas.filter(
                    notificacao_institucional_estado=EstadoNotificacaoInstitucional.PENDENTE
                ).count(),
                "cor": "danger",
                "icone": "alert-triangle",
            },
            {
                "titulo": "Pedidos da Cozinha em aberto",
                "valor": PedidoCozinha.objects.exclude(
                    estado__in=[EstadoPedidoCozinha.ENTREGUE, EstadoPedidoCozinha.CANCELADO]
                ).count(),
                "cor": "info",
                "icone": "coffee",
            },
        ],
    )


@login_required
@grupos_permitidos(GRUPO_COORDENACAO)
def dashboard_utentes(request):
    formulario, inicio, fim = intervalo(request, FiltroUtentesForm)
    dados = formulario.cleaned_data if formulario.is_valid() else {}
    utentes = Utente.objects.select_related("quarto")
    if dados.get("piso"):
        utentes = utentes.filter(quarto__piso=dados["piso"])
    if dados.get("tipo_internamento"):
        utentes = utentes.filter(tipo_internamento=dados["tipo_internamento"])
    if dados.get("genero"):
        utentes = utentes.filter(genero=dados["genero"])
    if dados.get("situacao") == "ATIVO":
        utentes = utentes.filter(data_saida__isnull=True)
    elif dados.get("situacao") == "ALTA":
        utentes = utentes.filter(data_saida__isnull=False)

    ativos = utentes.filter(data_saida__isnull=True)
    entradas_periodo = utentes.filter(data_entrada__range=(inicio, fim))
    altas_periodo = utentes.filter(data_saida__range=(inicio, fim))
    hoje = timezone.localdate()
    altas_7_dias = ativos.filter(data_prevista_saida__range=(hoje, hoje + timedelta(days=7)))
    etiquetas, entradas = serie_data(utentes, "data_entrada", inicio, fim)
    _, altas = serie_data(utentes, "data_saida", inicio, fim)
    por_piso = ativos.values("quarto__piso").annotate(total=Count("pk")).order_by("quarto__piso")
    por_internamento = (
        ativos.values("tipo_internamento").annotate(total=Count("pk")).order_by("-total")
    )

    proximas = ativos.filter(data_prevista_saida__isnull=False).order_by(
        "data_prevista_saida", "nome"
    )[:15]
    linhas = [
        {
            "celulas": [
                item.nome,
                item.numero_processo,
                escolha(Utente._meta.get_field("tipo_internamento").choices, item.tipo_internamento),
                str(item.quarto or "—"),
                formatar_data(item.data_prevista_saida),
            ],
            "url": reverse("visitas:detalhe_utente", args=[item.pk]),
        }
        for item in proximas
    ]
    return render_dashboard(
        request,
        pagina=pagina(
            "Utentes e internamentos",
            "Ocupação, movimentos e altas previstas por piso e tipologia.",
            "users",
            "primary",
        ),
        formulario=formulario,
        inicio=inicio,
        fim=fim,
        metricas=[
            metrica("Utentes ativos", ativos.count(), "users", "primary"),
            metrica("Entradas", entradas_periodo.count(), "log-in", "success", "no período"),
            metrica("Altas", altas_periodo.count(), "log-out", "info", "no período"),
            metrica("Altas nos próximos 7 dias", altas_7_dias.count(), "calendar", "warning"),
            metrica("Visitas restritas", ativos.filter(visitas_restritas=True).count(), "shield", "danger"),
        ],
        graficos=[
            grafico_area(
                "movimentos-utentes",
                "Entradas e altas",
                etiquetas,
                [{"name": "Entradas", "data": entradas}, {"name": "Altas", "data": altas}],
            ),
            grafico_donut(
                "utentes-piso",
                "Ocupação por piso",
                [linha["quarto__piso"] or "Sem piso" for linha in por_piso],
                [linha["total"] for linha in por_piso],
            ),
            grafico_barras(
                "utentes-internamento",
                "Utentes ativos por internamento",
                [
                    escolha(
                        Utente._meta.get_field("tipo_internamento").choices,
                        linha["tipo_internamento"],
                    )
                    for linha in por_internamento
                ],
                [linha["total"] for linha in por_internamento],
                "col-12",
            ),
        ],
        tabela={
            "titulo": "Planeamento de altas",
            "cabecalhos": ["Utente", "Processo", "Internamento", "Quarto", "Data prevista"],
            "linhas": linhas,
            "vazio": "Não existem altas planeadas para os filtros escolhidos.",
        },
    )


@login_required
@grupos_permitidos(GRUPO_COORDENACAO)
def dashboard_visitas(request):
    formulario, inicio, fim = intervalo(request, FiltroVisitasForm)
    dados = formulario.cleaned_data if formulario.is_valid() else {}
    visitas = Visita.objects.select_related("utente", "utente__quarto")
    if dados.get("piso"):
        visitas = visitas.filter(utente__quarto__piso=dados["piso"])
    if dados.get("tipo_visitante"):
        visitas = visitas.filter(tipo_visitante=dados["tipo_visitante"])

    periodo = visitas.filter(data_hora_entrada__date__range=(inicio, fim))
    em_curso = visitas.filter(data_hora_saida__isnull=True)
    externos = Externo.objects.filter(data_hora_entrada__date__range=(inicio, fim))
    etiquetas, visitas_dia = serie_contagem(visitas, "data_hora_entrada", inicio, fim)
    _, externos_dia = serie_contagem(Externo.objects.all(), "data_hora_entrada", inicio, fim)
    tipo_labels, tipo_values = distribuicao(
        periodo, "tipo_visitante", Visita._meta.get_field("tipo_visitante").choices
    )
    horas_labels, horas_values = serie_horas_entrada(
        periodo,
        "data_hora_entrada",
        hora_inicio=6,
        hora_fim=21,
    )
    total_dias_calendario = max(
        (fim - inicio).days + 1,
        1,
    )
    mes_inicio = MESES_PORTUGUES[inicio.month]
    mes_fim = MESES_PORTUGUES[fim.month]

    if inicio.year == fim.year and inicio.month == fim.month:
        periodo_grafico = f"{mes_inicio} de {inicio.year}"
    elif inicio.year == fim.year:
        periodo_grafico = (
            f"{mes_inicio}–{mes_fim} de {inicio.year}"
        )
    else:
        periodo_grafico = (
            f"{mes_inicio} de {inicio.year}–"
            f"{mes_fim} de {fim.year}"
        )

    horas_media_diaria = [
        round(total / total_dias_calendario, 2)
        for total in horas_values
    ]
    grafico_media_horaria = grafico_barras(
        "visitas-media-diaria-hora",
        "Média diária de visitas por hora de entrada",
        horas_labels,
        horas_media_diaria,
        "col-12",
        mostrar_valores=True,
    )
    grafico_media_horaria["descricao"] = (
        f"{periodo_grafico} · Total de cada faixa horária dividido por "
        f"{total_dias_calendario} dias de calendário."
    )
    por_piso = (
        periodo.values("utente__quarto__piso").annotate(total=Count("pk")).order_by("utente__quarto__piso")
    )
    linhas = [
        {
            "celulas": [
                item.nome_visitante,
                item.utente.nome,
                str(item.utente.quarto or "—"),
                formatar_data(item.data_hora_entrada, "d/m/Y H:i"),
                "Em curso",
            ]
        }
        for item in em_curso.order_by("data_hora_entrada")[:20]
    ]
    graficos_visitas = [
        grafico_barras(
            "visitas-hora-entrada",
            "Visitas por hora de entrada (06:00–21:00)",
            horas_labels,
            horas_values,
            "col-12",
            mostrar_valores=True,
        ),
        grafico_media_horaria,
        grafico_area(
            "visitas-diarias",
            "Entradas diárias",
            etiquetas,
            [
                {"name": "Visitas", "data": visitas_dia},
                {"name": "Externos/serviços", "data": externos_dia},
            ],
        ),
        grafico_donut(
            "visitas-tipo",
            "Tipo de visitante",
            tipo_labels,
            tipo_values,
        ),
        grafico_barras(
            "visitas-piso",
            "Visitas por piso",
            [linha["utente__quarto__piso"] or "Sem piso" for linha in por_piso],
            [linha["total"] for linha in por_piso],
            "col-12",
        ),
    ]

    for grafico in graficos_visitas:
        grafico.setdefault("descricao", periodo_grafico)

    pagina_visitas = pagina(
        "Visitas e entradas externas",
        "Fluxo de visitantes, permanências em curso e procura por piso.",
        "user-check",
        "success",
    )
    url_pdf = reverse("coordenacao:relatorio_visitas_pdf")
    parametros = request.GET.urlencode()
    if parametros:
        url_pdf = f"{url_pdf}?{parametros}"
    pagina_visitas["pdf_url"] = url_pdf

    return render_dashboard(
        request,
        pagina=pagina_visitas,
        formulario=formulario,
        inicio=inicio,
        fim=fim,
        metricas=[
            metrica("Visitas", periodo.count(), "user-check", "success", "no período"),
            metrica("Visitas concluídas", periodo.filter(data_hora_saida__isnull=False).count(), "check-circle", "primary"),
            metrica("Em curso agora", em_curso.count(), "clock", "warning"),
            metrica("Utentes visitados", periodo.values("utente_id").distinct().count(), "users", "info"),
            metrica("Entradas externas", externos.count(), "briefcase", "secondary", "no período"),
        ],
        graficos=graficos_visitas,
        tabela={
            "titulo": "Visitas atualmente em curso",
            "cabecalhos": ["Visitante", "Utente", "Quarto", "Entrada", "Situação"],
            "linhas": linhas,
            "vazio": "Não existem visitas em curso para os filtros escolhidos.",
        },
    )


@login_required
@grupos_permitidos(GRUPO_COORDENACAO)
def dashboard_transportes(request):
    formulario, inicio, fim = intervalo(request, FiltroTransportesForm)
    dados = formulario.cleaned_data if formulario.is_valid() else {}
    transportes = Transporte.objects.select_related("utente", "utente__quarto", "viatura", "condutor")
    if dados.get("piso"):
        transportes = transportes.filter(utente__quarto__piso=dados["piso"])
    if dados.get("estado"):
        transportes = transportes.filter(estado=dados["estado"])
    if dados.get("meio"):
        transportes = transportes.filter(meio_transporte=dados["meio"])
    if dados.get("tipo_deslocacao"):
        transportes = transportes.filter(tipo_deslocacao=dados["tipo_deslocacao"])

    periodo = transportes.filter(data_hora_saida__date__range=(inicio, fim))
    etiquetas, valores_dia = serie_contagem(transportes, "data_hora_saida", inicio, fim)
    estado_labels, estado_values = distribuicao(periodo, "estado", EstadoTransporte.choices)
    meio_labels, meio_values = distribuicao(periodo, "meio_transporte", MeioTransporte.choices)
    proximos = transportes.filter(data_hora_saida__gte=timezone.now()).exclude(
        estado=EstadoTransporte.CANCELADO
    ).order_by("data_hora_saida")[:20]
    linhas = [
        {
            "celulas": [
                formatar_data(item.data_hora_saida, "d/m/Y H:i"),
                item.utente.nome,
                item.destino,
                item.get_meio_transporte_display(),
                item.get_estado_display(),
            ],
            "url": reverse("visitas:detalhe_transporte", args=[item.pk]),
        }
        for item in proximos
    ]
    return render_dashboard(
        request,
        pagina=pagina(
            "Transportes",
            "Pedidos, planeamento e execução das deslocações dos utentes.",
            "truck",
            "info",
        ),
        formulario=formulario,
        inicio=inicio,
        fim=fim,
        metricas=[
            metrica("Transportes", periodo.count(), "truck", "info", "no período"),
            metrica("Pendentes", periodo.filter(estado=EstadoTransporte.PENDENTE).count(), "clock", "warning"),
            metrica("Confirmados", periodo.filter(estado=EstadoTransporte.CONFIRMADO).count(), "check-circle", "primary"),
            metrica("Em curso", transportes.filter(estado=EstadoTransporte.EM_CURSO).count(), "navigation", "secondary", "agora"),
            metrica("Concluídos", periodo.filter(estado=EstadoTransporte.CONCLUIDO).count(), "flag", "success"),
            metrica(
                "Pedidos por validar",
                PedidoTransporte.objects.filter(estado=EstadoPedidoTransporte.POR_VALIDAR).count(),
                "alert-circle",
                "danger",
                "na Receção",
            ),
        ],
        graficos=[
            grafico_area(
                "transportes-diarios",
                "Transportes por dia",
                etiquetas,
                [{"name": "Transportes", "data": valores_dia}],
            ),
            grafico_donut("transportes-estado", "Distribuição por estado", estado_labels, estado_values),
            grafico_barras("transportes-meio", "Meios de transporte", meio_labels, meio_values, "col-12"),
        ],
        tabela={
            "titulo": "Próximos transportes",
            "cabecalhos": ["Saída", "Utente", "Destino", "Meio", "Estado"],
            "linhas": linhas,
            "vazio": "Não existem próximos transportes para os filtros escolhidos.",
        },
    )


@login_required
@grupos_permitidos(GRUPO_COORDENACAO)
def dashboard_enfermagem(request):
    formulario, inicio, fim = intervalo(request, FiltroEnfermagemForm)
    dados = formulario.cleaned_data if formulario.is_valid() else {}
    registos = RegistoEnfermagem.objects.select_related(
        "utente", "utente__quarto", "tipo_registo", "profissional"
    )
    quedas = RegistoQueda.objects.select_related(
        "registo_enfermagem__utente",
        "registo_enfermagem__utente__quarto",
        "registo_enfermagem__profissional",
    )
    isolamentos = Isolamento.objects.select_related("utente", "utente__quarto")
    if dados.get("piso"):
        registos = registos.filter(utente__quarto__piso=dados["piso"])
        quedas = quedas.filter(registo_enfermagem__utente__quarto__piso=dados["piso"])
        isolamentos = isolamentos.filter(utente__quarto__piso=dados["piso"])
    if dados.get("turno"):
        registos = registos.filter(turno=dados["turno"])
    if dados.get("tipo_registo"):
        registos = registos.filter(tipo_registo=dados["tipo_registo"])
    if dados.get("profissional"):
        registos = registos.filter(profissional=dados["profissional"])
        quedas = quedas.filter(registo_enfermagem__profissional=dados["profissional"])
    if dados.get("gravidade"):
        quedas = quedas.filter(gravidade=dados["gravidade"])

    registos_periodo = registos.filter(data_registo__date__range=(inicio, fim))
    quedas_periodo = quedas.filter(data_hora_queda__date__range=(inicio, fim))
    ultimas_24h = quedas.filter(data_hora_queda__gte=timezone.now() - timedelta(hours=24))
    etiquetas, registos_dia = serie_contagem(registos, "data_registo", inicio, fim)
    _, quedas_dia = serie_contagem(quedas, "data_hora_queda", inicio, fim)
    gravidade_labels, gravidade_values = distribuicao(
        quedas_periodo, "gravidade", GravidadeQueda.choices
    )
    por_tipo = (
        registos_periodo.values("tipo_registo__nome").annotate(total=Count("pk")).order_by("-total")[:10]
    )
    linhas = [
        {
            "celulas": [
                formatar_data(item.data_hora_queda, "d/m/Y H:i"),
                item.utente.nome,
                str(item.utente.quarto or "—"),
                item.get_gravidade_display(),
                item.get_notificacao_institucional_estado_display(),
                nome_utilizador(item.profissional),
            ]
        }
        for item in quedas_periodo.order_by("-data_hora_queda")[:20]
    ]
    return render_dashboard(
        request,
        pagina=pagina(
            "Enfermagem e segurança",
            "Registos assistenciais, quedas, notificações e isolamentos.",
            "heart",
            "danger",
        ),
        formulario=formulario,
        inicio=inicio,
        fim=fim,
        metricas=[
            metrica("Registos de Enfermagem", registos_periodo.count(), "file-text", "primary", "no período"),
            metrica("Quedas", quedas_periodo.count(), "alert-triangle", "danger", "no período"),
            metrica("Quedas nas últimas 24 h", ultimas_24h.count(), "clock", "warning"),
            metrica(
                "Notificações pendentes",
                quedas.filter(
                    notificacao_institucional_estado=EstadoNotificacaoInstitucional.PENDENTE
                ).count(),
                "bell",
                "secondary",
            ),
            metrica("Isolamentos ativos", isolamentos.filter(ativo=True).count(), "shield", "info"),
        ],
        graficos=[
            grafico_area(
                "enfermagem-diario",
                "Registos e quedas por dia",
                etiquetas,
                [
                    {"name": "Registos", "data": registos_dia},
                    {"name": "Quedas", "data": quedas_dia},
                ],
            ),
            grafico_donut("quedas-gravidade", "Gravidade das quedas", gravidade_labels, gravidade_values),
            grafico_barras(
                "enfermagem-tipo",
                "Registos por tipo",
                [linha["tipo_registo__nome"] or "Sem tipo" for linha in por_tipo],
                [linha["total"] for linha in por_tipo],
                "col-12",
            ),
        ],
        tabela={
            "titulo": "Quedas no período",
            "cabecalhos": ["Data", "Utente", "Quarto", "Gravidade", "Notificação", "Profissional"],
            "linhas": linhas,
            "vazio": "Não existem quedas para os filtros escolhidos.",
        },
    )


@login_required
@grupos_permitidos(GRUPO_COORDENACAO)
def dashboard_fisioterapia(request):
    formulario, inicio, fim = intervalo(request, FiltroFisioterapiaForm)
    dados = formulario.cleaned_data if formulario.is_valid() else {}
    sessoes = SessaoFisioterapia.objects.select_related("profissional").prefetch_related(
        "participacoes__utente"
    )
    if dados.get("piso"):
        sessoes = sessoes.filter(participacoes__utente__quarto__piso=dados["piso"]).distinct()
    if dados.get("estado"):
        sessoes = sessoes.filter(estado=dados["estado"])
    if dados.get("tipo"):
        sessoes = sessoes.filter(tipo=dados["tipo"])
    if dados.get("profissional"):
        sessoes = sessoes.filter(profissional=dados["profissional"])

    periodo = sessoes.filter(inicio__date__range=(inicio, fim))
    participacoes = ParticipacaoFisioterapia.objects.filter(sessao__in=periodo)
    registos = RegistoFisioterapia.objects.filter(data_registo__date__range=(inicio, fim))
    if dados.get("piso"):
        registos = registos.filter(utente__quarto__piso=dados["piso"])
    if dados.get("profissional"):
        registos = registos.filter(profissional=dados["profissional"])

    etiquetas, sessoes_dia = serie_contagem(sessoes, "inicio", inicio, fim)
    estado_labels, estado_values = distribuicao(
        periodo, "estado", EstadoSessaoFisioterapia.choices
    )
    por_profissional = (
        periodo.values(
            "profissional__first_name",
            "profissional__last_name",
            "profissional__username",
        )
        .annotate(total=Count("pk", distinct=True))
        .order_by("-total")[:10]
    )
    nomes = [
        (
            f"{linha['profissional__first_name']} {linha['profissional__last_name']}".strip()
            or linha["profissional__username"]
        )
        for linha in por_profissional
    ]
    linhas = []
    for sessao in periodo.order_by("inicio")[:20]:
        participantes = [
            item
            for item in sessao.participacoes.all()
            if item.estado
            not in {
                EstadoParticipacaoFisioterapia.CANCELADO,
                EstadoParticipacaoFisioterapia.CANCELADO_ALTA,
            }
        ]
        local = getattr(sessao, "local_realizacao", "") or getattr(sessao, "local", "") or "—"
        if getattr(sessao, "local_realizacao", "") and hasattr(sessao, "get_local_realizacao_display"):
            local = sessao.get_local_realizacao_display()
        linhas.append(
            {
                "celulas": [
                    formatar_data(sessao.inicio, "d/m/Y H:i"),
                    sessao.get_tipo_display(),
                    str(len(participantes)),
                    nome_utilizador(sessao.profissional),
                    local,
                    sessao.get_estado_display(),
                ],
                "url": reverse("fisioterapia:detalhe_sessao", args=[sessao.pk]),
            }
        )
    return render_dashboard(
        request,
        pagina=pagina(
            "Fisioterapia e reabilitação",
            "Sessões, assiduidade, produção clínica e carga por profissional.",
            "activity",
            "warning",
        ),
        formulario=formulario,
        inicio=inicio,
        fim=fim,
        metricas=[
            metrica("Sessões", periodo.count(), "calendar", "warning", "no período"),
            metrica("Realizadas", periodo.filter(estado=EstadoSessaoFisioterapia.REALIZADA).count(), "check-circle", "success"),
            metrica("Agendadas", periodo.filter(estado=EstadoSessaoFisioterapia.AGENDADA).count(), "clock", "primary"),
            metrica("Canceladas", periodo.filter(estado=EstadoSessaoFisioterapia.CANCELADA).count(), "x-circle", "secondary"),
            metrica("Participações realizadas", participacoes.filter(estado=EstadoParticipacaoFisioterapia.REALIZADO).count(), "user-check", "info"),
            metrica("Faltas", participacoes.filter(estado=EstadoParticipacaoFisioterapia.FALTOU).count(), "user-x", "danger"),
            metrica("Registos clínicos", registos.count(), "file-text", "primary"),
        ],
        graficos=[
            grafico_area(
                "fisioterapia-diario",
                "Sessões por dia",
                etiquetas,
                [{"name": "Sessões", "data": sessoes_dia}],
            ),
            grafico_donut("fisioterapia-estado", "Estado das sessões", estado_labels, estado_values),
            grafico_barras(
                "fisioterapia-profissional",
                "Sessões por profissional",
                nomes,
                [linha["total"] for linha in por_profissional],
                "col-12",
            ),
        ],
        tabela={
            "titulo": "Sessões do período",
            "cabecalhos": ["Data", "Tipo", "Utentes", "Profissional", "Local", "Estado"],
            "linhas": linhas,
            "vazio": "Não existem sessões para os filtros escolhidos.",
        },
    )


@login_required
@grupos_permitidos(GRUPO_COORDENACAO)
def dashboard_cozinha(request):
    formulario, inicio, fim = intervalo(request, FiltroCozinhaForm)
    dados = formulario.cleaned_data if formulario.is_valid() else {}
    pedidos = PedidoCozinha.objects.select_related("unidade", "enviado_por", "entregue_por")
    if dados.get("unidade"):
        pedidos = pedidos.filter(unidade=dados["unidade"])
    if dados.get("tipo"):
        pedidos = pedidos.filter(tipo=dados["tipo"])
    if dados.get("estado"):
        pedidos = pedidos.filter(estado=dados["estado"])
    periodo = pedidos.filter(data_servico__range=(inicio, fim))

    refeicoes = LinhaRefeicaoPedido.objects.filter(pedido__in=periodo)
    produtos = LinhaProdutoPedido.objects.filter(pedido__in=periodo)
    total_refeicoes = refeicoes.aggregate(total=Coalesce(Sum("quantidade_solicitada"), 0))["total"]
    consumidas = refeicoes.aggregate(total=Coalesce(Sum("quantidade_consumida"), 0))["total"]
    suplementos = produtos.aggregate(
        total=Coalesce(
            Sum("quantidade_solicitada"),
            0,
            output_field=IntegerField(),
        )
    )["total"]
    etiquetas, refeicoes_dia = serie_data(
        pedidos.filter(tipo=TipoPedidoCozinha.REFEICOES), "data_servico", inicio, fim
    )
    _, suplementos_dia = serie_data(
        pedidos.filter(tipo=TipoPedidoCozinha.SUPLEMENTOS), "data_servico", inicio, fim
    )
    estado_labels, estado_values = distribuicao(periodo, "estado", EstadoPedidoCozinha.choices)
    por_unidade = periodo.values("unidade__nome").annotate(total=Count("pk")).order_by("-total")
    linhas = [
        {
            "celulas": [
                formatar_data(item.data_servico),
                item.unidade.nome,
                item.get_tipo_display(),
                item.get_estado_display(),
                nome_utilizador(item.enviado_por),
                formatar_data(item.entregue_em, "d/m/Y H:i") if item.entregue_em else "—",
            ],
            "url": reverse("cozinha:detalhe_pedido", args=[item.pk]),
        }
        for item in periodo.order_by("-data_servico", "unidade__ordem", "tipo")[:25]
    ]
    return render_dashboard(
        request,
        pagina=pagina(
            "Cozinha e alimentação",
            "Pedidos por unidade, produção, entregas e consumo de refeições e suplementos.",
            "coffee",
            "warning",
        ),
        formulario=formulario,
        inicio=inicio,
        fim=fim,
        metricas=[
            metrica("Pedidos", periodo.count(), "clipboard", "warning", "no período"),
            metrica("Refeições solicitadas", total_refeicoes, "coffee", "primary"),
            metrica("Refeições consumidas", consumidas, "check-circle", "success"),
            metrica("Suplementos solicitados", float(suplementos), "package", "info"),
            metrica("Em preparação", periodo.filter(estado=EstadoPedidoCozinha.EM_PREPARACAO).count(), "clock", "secondary"),
            metrica("Entregues", periodo.filter(estado=EstadoPedidoCozinha.ENTREGUE).count(), "truck", "success"),
            metrica("Com divergência", periodo.filter(estado=EstadoPedidoCozinha.DIVERGENCIA).count(), "alert-circle", "danger"),
        ],
        graficos=[
            grafico_area(
                "cozinha-diario",
                "Pedidos por dia",
                etiquetas,
                [
                    {"name": "Refeições", "data": refeicoes_dia},
                    {"name": "Suplementos", "data": suplementos_dia},
                ],
            ),
            grafico_donut("cozinha-estado", "Estado dos pedidos", estado_labels, estado_values),
            grafico_barras(
                "cozinha-unidade",
                "Pedidos por unidade/piso",
                [linha["unidade__nome"] for linha in por_unidade],
                [linha["total"] for linha in por_unidade],
                "col-12",
            ),
        ],
        tabela={
            "titulo": "Pedidos no período",
            "cabecalhos": ["Data", "Unidade", "Tipo", "Estado", "Enviado por", "Entrega"],
            "linhas": linhas,
            "vazio": "Não existem pedidos para os filtros escolhidos.",
        },
    )


@login_required
@grupos_permitidos(GRUPO_COORDENACAO)
def dashboard_financeiro(request):
    formulario, inicio, fim = intervalo(request, FiltroFinanceiroForm)
    dados = formulario.cleaned_data if formulario.is_valid() else {}
    movimentos = MovimentoFinanceiro.objects.select_related(
        "utente", "utente__quarto", "registado_por"
    )
    utentes = Utente.objects.select_related("quarto")
    if dados.get("piso"):
        movimentos = movimentos.filter(utente__quarto__piso=dados["piso"])
        utentes = utentes.filter(quarto__piso=dados["piso"])
    if dados.get("tipo"):
        movimentos = movimentos.filter(tipo=dados["tipo"])
    periodo = movimentos.filter(data__date__range=(inicio, fim))
    entradas = periodo.filter(tipo=MovimentoFinanceiro.ENTRADA)
    saidas = periodo.filter(tipo=MovimentoFinanceiro.SAIDA)
    total_entradas = entradas.aggregate(
        total=Coalesce(Sum("valor"), Decimal("0.00"))
    )["total"]
    total_saidas = saidas.aggregate(
        total=Coalesce(Sum("valor"), Decimal("0.00"))
    )["total"]
    saldo_contas = utentes.aggregate(
        total=Coalesce(Sum("saldo"), Decimal("0.00"))
    )["total"]
    etiquetas, entradas_dia = serie_soma(entradas, "data", "valor", inicio, fim)
    _, saidas_dia = serie_soma(saidas, "data", "valor", inicio, fim)
    maiores_saldos = utentes.order_by("-saldo")[:10]
    linhas = [
        {
            "celulas": [
                formatar_data(item.data, "d/m/Y H:i"),
                item.utente.nome,
                item.get_tipo_display(),
                f"{float(item.valor):.2f} €",
                item.descricao,
                nome_utilizador(item.registado_por),
            ],
            "url": reverse("visitas:financeiro_utente", args=[item.utente_id]),
        }
        for item in periodo.order_by("-data")[:25]
    ]
    return render_dashboard(
        request,
        pagina=pagina(
            "Financeiro",
            "Movimentos, saldos e contas dos utentes por período e piso.",
            "credit-card",
            "success",
        ),
        formulario=formulario,
        inicio=inicio,
        fim=fim,
        metricas=[
            metrica("Entradas", f"{float(total_entradas):.2f} €", "arrow-down-circle", "success", "no período"),
            metrica("Saídas", f"{float(total_saidas):.2f} €", "arrow-up-circle", "danger", "no período"),
            metrica("Resultado do período", f"{float(total_entradas - total_saidas):.2f} €", "trending-up", "primary"),
            metrica("Movimentos", periodo.count(), "repeat", "info"),
            metrica("Saldo atual das contas", f"{float(saldo_contas):.2f} €", "credit-card", "warning"),
            metrica("Contas com saldo negativo", utentes.filter(saldo__lt=0).count(), "alert-circle", "danger"),
        ],
        graficos=[
            grafico_area(
                "financeiro-diario",
                "Entradas e saídas diárias",
                etiquetas,
                [
                    {"name": "Entradas (€)", "data": entradas_dia},
                    {"name": "Saídas (€)", "data": saidas_dia},
                ],
            ),
            grafico_donut(
                "financeiro-mix",
                "Movimentos por tipo",
                ["Entradas", "Saídas"],
                [entradas.count(), saidas.count()],
            ),
            grafico_barras(
                "financeiro-saldos",
                "Maiores saldos atuais",
                [item.nome for item in maiores_saldos],
                [float(item.saldo) for item in maiores_saldos],
                "col-12",
            ),
        ],
        tabela={
            "titulo": "Movimentos no período",
            "cabecalhos": ["Data", "Utente", "Tipo", "Valor", "Descrição", "Registado por"],
            "linhas": linhas,
            "vazio": "Não existem movimentos para os filtros escolhidos.",
        },
    )
