from datetime import timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from config.decorators import grupos_permitidos
from fisioterapia.models import (
    AreaReabilitacao,
    EstadoParticipacaoFisioterapia,
    EstadoSessaoFisioterapia,
    ParticipacaoFisioterapia,
)
from visitas.models import Piso

from .models import (
    AusenciaUtente,
    EstadoAusenciaUtente,
    RegistoQueda,
)


GRUPO_ENFERMAGEM = "UCCI_Enfermagem"
GRUPO_COORDENACAO = "UCCI_Coordenacao"


def _converter_data_hora(valor):
    data_hora = parse_datetime(valor) if valor else None

    if (
        data_hora
        and settings.USE_TZ
        and timezone.is_naive(data_hora)
    ):
        data_hora = timezone.make_aware(
            data_hora,
            timezone.get_current_timezone(),
        )

    return data_hora


def _nome_profissional(profissional):
    return (
        profissional.get_full_name().strip()
        or profissional.username
    )


def _piso_utente(utente):
    if not utente.quarto_id:
        return "", "Sem piso"

    return (
        utente.quarto.piso,
        utente.quarto.get_piso_display(),
    )


def _classe_estado(estado):
    if estado == EstadoParticipacaoFisioterapia.REALIZADO:
        return "reab-realizado"

    if estado == EstadoParticipacaoFisioterapia.FALTOU:
        return "reab-faltou"

    if estado == EstadoParticipacaoFisioterapia.CANCELADO_AUSENCIA:
        return "reab-ausencia"

    if estado in {
        EstadoParticipacaoFisioterapia.CANCELADO,
        EstadoParticipacaoFisioterapia.CANCELADO_ALTA,
    }:
        return "reab-cancelado"

    return "reab-agendado"


def _prefixo_estado(estado, tem_queda_recente=False):
    prefixos = {
        EstadoParticipacaoFisioterapia.REALIZADO: "✓",
        EstadoParticipacaoFisioterapia.FALTOU: "✕",
        EstadoParticipacaoFisioterapia.CANCELADO: "—",
        EstadoParticipacaoFisioterapia.CANCELADO_ALTA: "—",
        EstadoParticipacaoFisioterapia.CANCELADO_AUSENCIA: "⏸",
    }

    partes = []

    if tem_queda_recente:
        partes.append("⚠")

    if estado in prefixos:
        partes.append(prefixos[estado])

    return " ".join(partes)


def _ausencia_abrange_sessao(ausencia, sessao):
    if not ausencia:
        return False

    fim_ausencia = (
        ausencia.data_hora_regresso
        or ausencia.data_hora_fim_prevista
    )

    return (
        ausencia.data_hora_inicio < sessao.fim
        and (
            fim_ausencia is None
            or fim_ausencia > sessao.inicio
        )
    )


@login_required
@grupos_permitidos(
    GRUPO_ENFERMAGEM,
    GRUPO_COORDENACAO,
)
def calendario_reabilitacao_enfermagem(request):
    hoje = timezone.localdate()
    agora = timezone.now()
    limite_quedas = agora - timedelta(hours=24)

    participacoes_hoje = (
        ParticipacaoFisioterapia.objects
        .filter(sessao__inicio__date=hoje)
    )

    context = {
        "pisos": Piso.choices,
        "areas": AreaReabilitacao.choices,
        "estados_participacao": (
            EstadoParticipacaoFisioterapia.choices
        ),
        "total_marcacoes_hoje": (
            participacoes_hoje.count()
        ),
        "total_agendadas_hoje": (
            participacoes_hoje.filter(
                estado=(
                    EstadoParticipacaoFisioterapia.AGENDADO
                )
            ).count()
        ),
        "total_ausencias_ativas": (
            AusenciaUtente.objects.filter(
                estado=EstadoAusenciaUtente.ATIVA
            ).count()
        ),
        "total_quedas_24h": (
            RegistoQueda.objects.filter(
                data_hora_queda__gte=limite_quedas,
                data_hora_queda__lte=agora,
            )
            .values(
                "registo_enfermagem__utente_id"
            )
            .distinct()
            .count()
        ),
    }

    return render(
        request,
        "enfermagem/calendario_reabilitacao.html",
        context,
    )


@login_required
@grupos_permitidos(
    GRUPO_ENFERMAGEM,
    GRUPO_COORDENACAO,
)
def eventos_reabilitacao_enfermagem(request):
    inicio = _converter_data_hora(
        request.GET.get("start")
    )
    fim = _converter_data_hora(
        request.GET.get("end")
    )
    piso = request.GET.get("piso", "").strip()
    area = request.GET.get("area", "").strip()
    estado = request.GET.get("estado", "").strip()

    participacoes = (
        ParticipacaoFisioterapia.objects
        .select_related(
            "sessao",
            "sessao__profissional",
            "utente",
            "utente__quarto",
            "cancelada_por_ausencia",
        )
        .prefetch_related(
            "sessao__tipos_intervencao"
        )
    )

    if inicio:
        participacoes = participacoes.filter(
            sessao__fim__gt=inicio
        )

    if fim:
        participacoes = participacoes.filter(
            sessao__inicio__lt=fim
        )

    if piso:
        participacoes = participacoes.filter(
            utente__quarto__piso=piso
        )

    if area:
        participacoes = participacoes.filter(
            sessao__area=area
        )

    if estado:
        participacoes = participacoes.filter(
            estado=estado
        )

    agora = timezone.now()
    limite_quedas = agora - timedelta(hours=24)

    quedas_recentes = (
        RegistoQueda.objects
        .filter(
            data_hora_queda__gte=limite_quedas,
            data_hora_queda__lte=agora,
        )
        .select_related(
            "registo_enfermagem__utente"
        )
        .order_by("-data_hora_queda")
    )

    queda_por_utente = {}

    for queda in quedas_recentes:
        queda_por_utente.setdefault(
            queda.utente.pk,
            queda,
        )

    ausencias_ativas = (
        AusenciaUtente.objects
        .filter(estado=EstadoAusenciaUtente.ATIVA)
        .select_related("utente")
    )
    ausencia_por_utente = {
        ausencia.utente_id: ausencia
        for ausencia in ausencias_ativas
    }

    eventos = []

    for participacao in participacoes:
        sessao = participacao.sessao
        utente = participacao.utente
        queda = queda_por_utente.get(utente.pk)
        ausencia = participacao.cancelada_por_ausencia

        if ausencia is None:
            ausencia_ativa = ausencia_por_utente.get(
                utente.pk
            )

            if _ausencia_abrange_sessao(
                ausencia_ativa,
                sessao,
            ):
                ausencia = ausencia_ativa

        estado_visual = participacao.estado

        if (
            sessao.estado
            == EstadoSessaoFisioterapia.CANCELADA
            and estado_visual
            == EstadoParticipacaoFisioterapia.AGENDADO
        ):
            estado_visual = (
                EstadoParticipacaoFisioterapia.CANCELADO
            )

        if (
            ausencia
            and estado_visual
            == EstadoParticipacaoFisioterapia.AGENDADO
        ):
            estado_visual = (
                EstadoParticipacaoFisioterapia.CANCELADO_AUSENCIA
            )

        prefixo = _prefixo_estado(
            estado_visual,
            tem_queda_recente=bool(queda),
        )
        titulo = (
            f"{utente.nome} · {sessao.get_area_display()}"
        )

        if prefixo:
            titulo = f"{prefixo} {titulo}"

        piso_valor, piso_nome = _piso_utente(utente)
        intervencoes = [
            item.nome
            for item in sessao.tipos_intervencao.all()
        ]

        eventos.append({
            "id": f"participacao-{participacao.pk}",
            "groupId": f"sessao-{sessao.pk}",
            "title": titulo,
            "start": sessao.inicio.isoformat(),
            "end": sessao.fim.isoformat(),
            "backgroundColor": sessao.cor_calendario,
            "borderColor": sessao.cor_calendario,
            "classNames": [
                "reab-evento",
                _classe_estado(estado_visual),
            ],
            "extendedProps": {
                "utente": utente.nome,
                "processo": utente.numero_processo,
                "area": sessao.get_area_display(),
                "tipo": sessao.get_tipo_display(),
                "estado": (
                    EstadoParticipacaoFisioterapia(
                        estado_visual
                    ).label
                ),
                "estado_codigo": estado_visual,
                "profissional": _nome_profissional(
                    sessao.profissional
                ),
                "piso": piso_nome,
                "piso_codigo": piso_valor,
                "quarto": (
                    str(utente.quarto)
                    if utente.quarto_id
                    else "Sem quarto"
                ),
                "local": sessao.local_exibicao,
                "intervencoes": intervencoes,
                "motivo_estado": (
                    participacao.motivo_estado or ""
                ),
                "ausencia": (
                    ausencia.get_tipo_display()
                    if ausencia
                    else ""
                ),
                "ausencia_destino": (
                    ausencia.destino
                    if ausencia
                    else ""
                ),
                "alerta_queda": bool(queda),
                "queda_em": (
                    timezone.localtime(
                        queda.data_hora_queda
                    ).strftime("%d/%m/%Y %H:%M")
                    if queda
                    else ""
                ),
                "queda_gravidade": (
                    queda.get_gravidade_display()
                    if queda
                    else ""
                ),
            },
        })

    return JsonResponse(eventos, safe=False)
