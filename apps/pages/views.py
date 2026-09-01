import json
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import render
from django.utils import timezone

from config.decorators import grupos_permitidos
from fisioterapia.models import (
    EstadoParticipacaoFisioterapia,
    EstadoSessaoFisioterapia,
    ParticipacaoFisioterapia,
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

from clinica.permissoes import filtrar_registos_visiveis
from enfermagem.models import (
    AREA_CLINICA_ENFERMAGEM,
    EstadoNotificacaoInstitucional,
    RegistoEnfermagem,
    RegistoQueda,
)

from .perfis import PERFIS_PORTAL


@login_required
@grupos_permitidos(
    "UCCI_Rececao",
    "UCCI_Coordenacao",
)
def dashboard_coordenacao(request):
    hoje = timezone.localdate()

    total_utentes_ativos = (
        Utente.objects
        .filter(data_saida__isnull=True)
        .count()
    )

    visitas_hoje = (
        Visita.objects
        .filter(data_hora_entrada__date=hoje)
        .count()
    )

    visitas_em_curso_qs = (
        Visita.objects
        .filter(data_hora_saida__isnull=True)
        .select_related(
            "utente",
            "utente__quarto",
        )
    )

    fim_janela = hoje + timedelta(days=5)

    proximas_altas = (
        Utente.objects
        .filter(
            data_prevista_saida__isnull=False,
            data_prevista_saida__range=(
                hoje,
                fim_janela,
            ),
            data_saida__isnull=True,
        )
        .order_by(
            "data_prevista_saida",
            "nome",
        )[:10]
    )

    dias = []
    entradas = []
    saidas = []

    for i in range(29, -1, -1):
        dia = hoje - timedelta(days=i)

        dias.append(
            dia.strftime("%d/%m")
        )

        entradas.append(
            Utente.objects.filter(
                data_entrada=dia
            ).count()
        )

        saidas.append(
            Utente.objects.filter(
                data_saida=dia
            ).count()
        )

    context = {
        "total_utentes_ativos": (
            total_utentes_ativos
        ),
        "visitas_hoje": visitas_hoje,
        "visitas_em_curso": (
            visitas_em_curso_qs.count()
        ),
        "lista_visitas_em_curso": (
            visitas_em_curso_qs
        ),
        "proximas_altas": proximas_altas,
        "grafico_dias": json.dumps(dias),
        "grafico_entradas": json.dumps(
            entradas
        ),
        "grafico_saidas": json.dumps(
            saidas
        ),
    }

    return render(
        request,
        "pages/dashboard_coordenacao.html",
        context,
    )


@login_required
def index(request):
    nomes_grupos = set(
        request.user.groups.values_list(
            "name",
            flat=True,
        )
    )

    perfis_disponiveis = []

    for nome_grupo, configuracao in (
        PERFIS_PORTAL.items()
    ):
        if (
            request.user.is_superuser
            or nome_grupo in nomes_grupos
        ):
            perfil = configuracao.copy()
            perfil["grupo"] = nome_grupo

            perfis_disponiveis.append(
                perfil
            )

    return render(
        request,
        "pages/index.html",
        {
            "perfis": perfis_disponiveis,
        },
    )


def obter_perfil_por_slug(slug):
    for nome_grupo, configuracao in (
        PERFIS_PORTAL.items()
    ):
        if configuracao["slug"] == slug:
            perfil = configuracao.copy()
            perfil["grupo"] = nome_grupo

            return perfil

    raise Http404(
        "Perfil não encontrado."
    )


@login_required
@grupos_permitidos("UCCI_Rececao")
def dashboard_recepcao(request):
    hoje = timezone.localdate()

    visitas_em_curso = (
        Visita.objects
        .filter(data_hora_saida__isnull=True)
        .select_related(
            "utente",
            "utente__quarto",
        )
        .order_by("data_hora_entrada")
    )

    externos_em_curso = (
        Externo.objects
        .filter(data_hora_saida__isnull=True)
        .order_by("data_hora_entrada")
    )

    transportes_hoje = (
        Transporte.objects
        .filter(data_hora_saida__date=hoje)
        .select_related(
            "utente",
            "viatura",
            "condutor",
        )
        .order_by("data_hora_saida")
    )

    pedidos_por_validar = (
        PedidoTransporte.objects
        .filter(
            estado=(
                EstadoPedidoTransporte.POR_VALIDAR
            )
        )
        .select_related(
            "utente",
            "pedido_por",
        )
        .order_by("criado_em")
    )

    externos_por_confirmar = (
        Transporte.objects
        .filter(
            estado=EstadoTransporte.PENDENTE
        )
        .exclude(
            meio_transporte=(
                MeioTransporte.INSTITUICAO
            )
        )
    )

    context = {
        "total_utentes_ativos": (
            Utente.objects
            .filter(data_saida__isnull=True)
            .count()
        ),
        "total_visitas_hoje": (
            Visita.objects
            .filter(
                data_hora_entrada__date=hoje
            )
            .count()
        ),
        "total_visitas_em_curso": (
            visitas_em_curso.count()
        ),
        "total_externos_em_curso": (
            externos_em_curso.count()
        ),
        "total_transportes_hoje": (
            transportes_hoje.count()
        ),
        "total_transportes_pendentes": (
            Transporte.objects
            .filter(
                estado=EstadoTransporte.PENDENTE
            )
            .count()
        ),
        "total_pedidos_por_validar": (
            pedidos_por_validar.count()
        ),
        "total_externos_por_confirmar": (
            externos_por_confirmar.count()
        ),
        "visitas_em_curso": (
            visitas_em_curso[:8]
        ),
        "externos_em_curso": (
            externos_em_curso[:8]
        ),
        "transportes_hoje": (
            transportes_hoje[:8]
        ),
        "pedidos_por_validar": (
            pedidos_por_validar[:8]
        ),
    }

    return render(
        request,
        "pages/perfis/rececao.html",
        context,
    )


def _metricas_perfil(
    slug,
    utilizador=None,
):
    utentes_ativos = (
        Utente.objects
        .filter(data_saida__isnull=True)
        .count()
    )

    pedidos_abertos = (
        PedidoTransporte.objects
        .filter(
            estado__in=(
                EstadoPedidoTransporte.POR_VALIDAR,
                EstadoPedidoTransporte.DEVOLVIDO,
            )
        )
        .count()
    )

    if slug == "enfermagem":
        hoje = timezone.localdate()

        if utilizador is None:
            registos_visiveis = (
                RegistoEnfermagem.objects.none()
            )
            quedas_visiveis = (
                RegistoQueda.objects.none()
            )
        else:
            registos_visiveis = (
                filtrar_registos_visiveis(
                    RegistoEnfermagem.objects.all(),
                    utilizador,
                    AREA_CLINICA_ENFERMAGEM,
                )
            )

            quedas_visiveis = (
                filtrar_registos_visiveis(
                    RegistoQueda.objects.all(),
                    utilizador,
                    AREA_CLINICA_ENFERMAGEM,
                    campo_autor=(
                        "registo_enfermagem__profissional_id"
                    ),
                    campo_visibilidade=(
                        "registo_enfermagem__visibilidade"
                    ),
                )
            )

        return [
            {
                "titulo": "Utentes ativos",
                "valor": utentes_ativos,
                "icone": "users",
            },
            {
                "titulo": "Registos hoje",
                "valor": (
                    registos_visiveis
                    .filter(
                        data_registo__date=hoje,
                    )
                    .count()
                ),
                "icone": "clipboard",
            },
            {
                "titulo": "Quedas por notificar",
                "valor": (
                    quedas_visiveis
                    .filter(
                        notificacao_institucional_estado=(
                            EstadoNotificacaoInstitucional.PENDENTE
                        ),
                    )
                    .count()
                ),
                "icone": "alert-triangle",
            },
            {
                "titulo": "Isolamentos ativos",
                "valor": (
                    Isolamento.objects
                    .filter(ativo=True)
                    .count()
                ),
                "icone": "shield",
            },
        ]

    if slug == "medicos":
        return [
            {
                "titulo": "Utentes ativos",
                "valor": utentes_ativos,
                "icone": "users",
            },
            {
                "titulo": "Isolamentos ativos",
                "valor": (
                    Isolamento.objects
                    .filter(ativo=True)
                    .count()
                ),
                "icone": "shield",
            },
            {
                "titulo": "Pedidos em tratamento",
                "valor": pedidos_abertos,
                "icone": "truck",
            },
        ]

    if slug == "servico-social":
        return [
            {
                "titulo": "Utentes ativos",
                "valor": utentes_ativos,
                "icone": "users",
            },
            {
                "titulo": "Pedidos em tratamento",
                "valor": pedidos_abertos,
                "icone": "truck",
            },
        ]

    if slug == "psicologia":
        return [
            {
                "titulo": "Utentes ativos",
                "valor": utentes_ativos,
                "icone": "users",
            },
        ]

    if slug == "fisioterapia":
        hoje = timezone.localdate()
        agora = timezone.now()

        sessoes_hoje = (
            SessaoFisioterapia.objects
            .filter(inicio__date=hoje)
            .exclude(
                estado=(
                    EstadoSessaoFisioterapia.CANCELADA
                )
            )
        )

        minhas_sessoes_hoje = sessoes_hoje

        if utilizador is not None:
            minhas_sessoes_hoje = (
                minhas_sessoes_hoje.filter(
                    profissional=utilizador
                )
            )
        else:
            minhas_sessoes_hoje = (
                minhas_sessoes_hoje.none()
            )

        presencas_por_validar = (
            ParticipacaoFisioterapia.objects
            .filter(
                estado=(
                    EstadoParticipacaoFisioterapia
                    .AGENDADO
                ),
                sessao__inicio__lt=agora,
            )
            .exclude(
                sessao__estado=(
                    EstadoSessaoFisioterapia.CANCELADA
                )
            )
        )

        if utilizador is not None:
            presencas_por_validar = (
                presencas_por_validar.filter(
                    sessao__profissional=utilizador
                )
            )
        else:
            presencas_por_validar = (
                presencas_por_validar.none()
            )

        return [
            {
                "titulo": "Utentes ativos",
                "valor": utentes_ativos,
                "icone": "users",
            },
            {
                "titulo": "Sessões da equipa hoje",
                "valor": sessoes_hoje.count(),
                "icone": "calendar",
            },
            {
                "titulo": "As minhas sessões hoje",
                "valor": minhas_sessoes_hoje.count(),
                "icone": "activity",
            },
            {
                "titulo": "Presenças por validar",
                "valor": presencas_por_validar.count(),
                "icone": "check-square",
            },
        ]

    if slug == "transportes":
        hoje = timezone.localdate()

        return [
            {
                "titulo": "Internos por confirmar",
                "valor": (
                    Transporte.objects
                    .filter(
                        estado=(
                            EstadoTransporte.PENDENTE
                        ),
                        meio_transporte=(
                            MeioTransporte.INSTITUICAO
                        ),
                    )
                    .count()
                ),
                "icone": "alert-circle",
            },
            {
                "titulo": "Transportes hoje",
                "valor": (
                    Transporte.objects
                    .filter(
                        data_hora_saida__date=hoje
                    )
                    .count()
                ),
                "icone": "calendar",
            },
            {
                "titulo": "Em curso",
                "valor": (
                    Transporte.objects
                    .filter(
                        estado=(
                            EstadoTransporte.EM_CURSO
                        )
                    )
                    .count()
                ),
                "icone": "navigation",
            },
        ]

    if slug == "financeiro":
        hoje = timezone.localdate()

        return [
            {
                "titulo": "Contas de utentes",
                "valor": Utente.objects.count(),
                "icone": "users",
            },
            {
                "titulo": "Contas com saldo",
                "valor": (
                    Utente.objects
                    .exclude(saldo=0)
                    .count()
                ),
                "icone": "credit-card",
            },
            {
                "titulo": "Movimentos hoje",
                "valor": (
                    MovimentoFinanceiro.objects
                    .filter(data__date=hoje)
                    .count()
                ),
                "icone": "repeat",
            },
        ]

    return []


@login_required
def perfil_inicio(request, slug):
    perfil = obter_perfil_por_slug(slug)

    pertence_ao_grupo = (
        request.user.groups
        .filter(name=perfil["grupo"])
        .exists()
    )

    if (
        not request.user.is_superuser
        and not pertence_ao_grupo
    ):
        raise PermissionDenied(
            "Não tem autorização para aceder a esta área."
        )

    if slug == "rececao":
        return dashboard_recepcao(request)

    if slug == "coordenacao":
        return dashboard_coordenacao(request)

    context = {
        "perfil": perfil,
        "metricas": _metricas_perfil(
            slug,
            request.user,
        ),
    }

    if slug == "enfermagem":
        quedas_recentes = (
            RegistoQueda.objects
            .select_related(
                "registo_enfermagem",
                "registo_enfermagem__utente",
                "registo_enfermagem__utente__quarto",
                "registo_enfermagem__profissional",
            )
        )

        quedas_recentes = (
            filtrar_registos_visiveis(
                quedas_recentes,
                request.user,
                AREA_CLINICA_ENFERMAGEM,
                campo_autor=(
                    "registo_enfermagem__profissional_id"
                ),
                campo_visibilidade=(
                    "registo_enfermagem__visibilidade"
                ),
            )
        )

        context["quedas_recentes"] = (
            quedas_recentes
            .order_by("-data_hora_queda")[:6]
        )

    if slug in {
        "enfermagem",
        "medicos",
        "servico-social",
    }:
        context["pedidos_recentes"] = (
            PedidoTransporte.objects
            .select_related(
                "utente",
                "pedido_por",
            )[:6]
        )

    if slug == "transportes":
        context["transportes_pendentes"] = (
            Transporte.objects
            .filter(
                estado=EstadoTransporte.PENDENTE,
                meio_transporte=(
                    MeioTransporte.INSTITUICAO
                ),
            )
            .select_related(
                "utente",
                "viatura",
                "condutor",
            )[:6]
        )

    if slug == "fisioterapia":
        hoje = timezone.localdate()

        context["sessoes_fisioterapia_hoje"] = (
            SessaoFisioterapia.objects
            .filter(inicio__date=hoje)
            .select_related(
                "profissional",
                "criado_por",
            )
            .prefetch_related(
                "participacoes__utente__quarto",
                "tipos_intervencao",
            )
            .order_by("inicio")[:8]
        )

        context["minhas_proximas_sessoes"] = (
            SessaoFisioterapia.objects
            .filter(
                profissional=request.user,
                inicio__gte=timezone.now(),
                estado=(
                    EstadoSessaoFisioterapia.AGENDADA
                ),
            )
            .select_related(
                "profissional",
                "criado_por",
            )
            .prefetch_related(
                "participacoes__utente__quarto",
                "tipos_intervencao",
            )
            .order_by("inicio")[:6]
        )

    return render(
        request,
        "pages/perfil_base.html",
        context,
    )


# Componentes mantidos pelo tema da aplicação.
def color(request):
    return render(
        request,
        "pages/color.html",
        {
            "segment": "color",
        },
    )


def typography(request):
    return render(
        request,
        "pages/typography.html",
        {
            "segment": "typography",
        },
    )


def icon_feather(request):
    return render(
        request,
        "pages/icon-feather.html",
        {
            "segment": "feather_icon",
        },
    )


def sample_page(request):
    return render(
        request,
        "pages/sample-page.html",
        {
            "segment": "sample_page",
        },
    )


@login_required
def acessos_rapidos(request):
    return render(
        request,
        "pages/acessos_rapidos.html",
    )
