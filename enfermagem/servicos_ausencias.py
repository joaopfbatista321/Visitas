from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from fisioterapia.models import (
    EstadoParticipacaoFisioterapia,
    EstadoSessaoFisioterapia,
    ParticipacaoFisioterapia,
)

from .models import (
    AcaoHistoricoAusencia,
    AusenciaUtente,
    EstadoAusenciaUtente,
    HistoricoAusenciaUtente,
)


ESTADOS_PARTICIPACAO_CANCELADOS = {
    EstadoParticipacaoFisioterapia.CANCELADO,
    EstadoParticipacaoFisioterapia.CANCELADO_ALTA,
    EstadoParticipacaoFisioterapia.CANCELADO_AUSENCIA,
}


def _fim_ausencia(ausencia):
    if ausencia.estado == EstadoAusenciaUtente.CANCELADA:
        return None

    if ausencia.estado == EstadoAusenciaUtente.TERMINADA:
        return ausencia.data_hora_regresso

    return ausencia.data_hora_fim_prevista


def _filtro_dentro_periodo(ausencia):
    filtro = Q(
        sessao__fim__gt=ausencia.data_hora_inicio,
    )

    fim = _fim_ausencia(ausencia)

    if fim:
        filtro &= Q(sessao__inicio__lt=fim)

    return filtro


def _atualizar_estado_sessao(sessao, utilizador):
    participacoes = sessao.participacoes.all()

    tem_participacao_ativa = participacoes.exclude(
        estado__in=ESTADOS_PARTICIPACAO_CANCELADOS,
    ).exists()

    novo_estado = None

    if (
        not tem_participacao_ativa
        and sessao.estado
        == EstadoSessaoFisioterapia.AGENDADA
    ):
        novo_estado = EstadoSessaoFisioterapia.CANCELADA

    elif (
        tem_participacao_ativa
        and sessao.estado
        == EstadoSessaoFisioterapia.CANCELADA
        and participacoes.filter(
            estado=EstadoParticipacaoFisioterapia.AGENDADO,
        ).exists()
    ):
        novo_estado = EstadoSessaoFisioterapia.AGENDADA

    if not novo_estado:
        return

    sessao.estado = novo_estado
    sessao.estado_atualizado_por = utilizador
    sessao.estado_atualizado_em = timezone.now()
    sessao.save(
        update_fields=[
            "estado",
            "estado_atualizado_por",
            "estado_atualizado_em",
            "atualizado_em",
        ]
    )


@transaction.atomic
def sincronizar_ausencia_reabilitacao(
    ausencia,
    utilizador,
):
    """
    Cancela marcações abrangidas pela ausência e repõe apenas
    marcações futuras que tenham sido canceladas por esta mesma
    ausência e já não coincidam com o período atual.
    """
    ausencia = (
        AusenciaUtente.objects
        .select_for_update()
        .select_related("utente")
        .get(pk=ausencia.pk)
    )

    agora = timezone.now()
    sessoes_afetadas = set()
    total_canceladas = 0
    total_repostas = 0

    canceladas_por_esta_ausencia = (
        ParticipacaoFisioterapia.objects
        .select_for_update()
        .select_related("sessao", "utente")
        .filter(
            utente=ausencia.utente,
            estado=(
                EstadoParticipacaoFisioterapia
                .CANCELADO_AUSENCIA
            ),
            cancelada_por_ausencia=ausencia,
        )
    )

    if ausencia.estado == EstadoAusenciaUtente.CANCELADA:
        para_repor = canceladas_por_esta_ausencia.filter(
            sessao__inicio__gte=agora,
        )
    else:
        dentro_periodo = _filtro_dentro_periodo(ausencia)

        para_cancelar = (
            ParticipacaoFisioterapia.objects
            .select_for_update()
            .select_related("sessao", "utente")
            .filter(
                dentro_periodo,
                utente=ausencia.utente,
                estado=EstadoParticipacaoFisioterapia.AGENDADO,
            )
        )

        motivo = (
            "Cancelamento automático por "
            f"{ausencia.get_tipo_display().lower()}."
        )

        for participacao in para_cancelar:
            participacao.alterar_estado(
                EstadoParticipacaoFisioterapia.CANCELADO_AUSENCIA,
                utilizador=utilizador,
                motivo=motivo,
                ausencia=ausencia,
            )
            sessoes_afetadas.add(participacao.sessao_id)
            total_canceladas += 1

        para_repor = (
            canceladas_por_esta_ausencia
            .filter(sessao__inicio__gte=agora)
            .exclude(dentro_periodo)
        )

    for participacao in para_repor:
        participacao.alterar_estado(
            EstadoParticipacaoFisioterapia.AGENDADO,
            utilizador=utilizador,
            motivo=(
                "Reposição automática após alteração "
                "ou cancelamento da ausência."
            ),
        )
        sessoes_afetadas.add(participacao.sessao_id)
        total_repostas += 1

    sessoes = {
        participacao.sessao_id: participacao.sessao
        for participacao in (
            ParticipacaoFisioterapia.objects
            .select_related("sessao")
            .filter(sessao_id__in=sessoes_afetadas)
        )
    }

    for sessao in sessoes.values():
        _atualizar_estado_sessao(
            sessao,
            utilizador,
        )

    return {
        "canceladas": total_canceladas,
        "repostas": total_repostas,
    }


@transaction.atomic
def guardar_ausencia(ausencia, utilizador):
    nova = ausencia.pk is None

    if nova:
        ausencia.criado_por = utilizador
        ausencia.estado = EstadoAusenciaUtente.ATIVA
    else:
        ausencia.estado_atualizado_por = utilizador
        ausencia.estado_atualizado_em = timezone.now()

    ausencia.full_clean()
    ausencia.save()

    HistoricoAusenciaUtente.objects.create(
        ausencia=ausencia,
        acao=(
            AcaoHistoricoAusencia.CRIADA
            if nova
            else AcaoHistoricoAusencia.ALTERADA
        ),
        dados=ausencia.dados_para_historico(),
        profissional=utilizador,
    )

    resultado = sincronizar_ausencia_reabilitacao(
        ausencia,
        utilizador,
    )

    return ausencia, resultado


@transaction.atomic
def terminar_ausencia(
    ausencia,
    utilizador,
    momento=None,
):
    ausencia = AusenciaUtente.objects.select_for_update().get(
        pk=ausencia.pk,
    )
    ausencia.terminar(
        utilizador=utilizador,
        momento=momento,
    )

    resultado = sincronizar_ausencia_reabilitacao(
        ausencia,
        utilizador,
    )

    return ausencia, resultado


@transaction.atomic
def cancelar_ausencia(ausencia, utilizador):
    ausencia = AusenciaUtente.objects.select_for_update().get(
        pk=ausencia.pk,
    )
    ausencia.cancelar(utilizador=utilizador)

    resultado = sincronizar_ausencia_reabilitacao(
        ausencia,
        utilizador,
    )

    return ausencia, resultado
