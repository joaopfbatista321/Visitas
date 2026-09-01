from django.core.exceptions import ValidationError
from django.db import transaction

from .models import (
    EstadoParticipacaoFisioterapia,
    EstadoSessaoFisioterapia,
    HistoricoParticipacaoFisioterapia,
    ParticipacaoFisioterapia,
)


ESTADOS_CANCELADOS = {
    EstadoParticipacaoFisioterapia.CANCELADO,
    EstadoParticipacaoFisioterapia.CANCELADO_ALTA,
}


def atualizar_estado_sessao(sessao):
    """
    Atualiza o estado geral da sessão conforme os estados
    individuais dos participantes.
    """
    estados = set(
        sessao.participacoes.values_list(
            "estado",
            flat=True,
        )
    )

    if not estados:
        novo_estado = EstadoSessaoFisioterapia.CANCELADA

    elif EstadoParticipacaoFisioterapia.AGENDADO in estados:
        novo_estado = EstadoSessaoFisioterapia.AGENDADA

    elif estados.intersection({
        EstadoParticipacaoFisioterapia.REALIZADO,
        EstadoParticipacaoFisioterapia.FALTOU,
    }):
        novo_estado = EstadoSessaoFisioterapia.REALIZADA

    else:
        novo_estado = EstadoSessaoFisioterapia.CANCELADA

    if sessao.estado != novo_estado:
        sessao.estado = novo_estado

        sessao.save(
            update_fields=[
                "estado",
                "atualizado_em",
            ]
        )


@transaction.atomic
def sincronizar_participantes(
    sessao,
    utentes,
    utilizador,
):
    """
    Adiciona os novos participantes, reativa cancelamentos
    manuais e cancela quem foi retirado da sessão.

    Os participantes nunca são eliminados, preservando
    sempre o histórico.
    """
    ids_selecionados = {
        utente.pk
        for utente in utentes
    }

    participacoes_existentes = {
        participacao.utente_id: participacao
        for participacao in (
            sessao.participacoes
            .select_for_update()
            .select_related("utente")
        )
    }

    for utente in utentes:
        if utente.data_saida:
            raise ValidationError(
                f"O utente {utente.nome} já tem alta."
            )

        participacao = participacoes_existentes.get(
            utente.pk
        )

        if participacao is None:
            participacao = (
                ParticipacaoFisioterapia.objects.create(
                    sessao=sessao,
                    utente=utente,
                    estado=(
                        EstadoParticipacaoFisioterapia.AGENDADO
                    ),
                )
            )

            HistoricoParticipacaoFisioterapia.objects.create(
                participacao=participacao,
                estado_anterior="",
                estado_novo=(
                    EstadoParticipacaoFisioterapia.AGENDADO
                ),
                alterado_por=utilizador,
                motivo="Utente adicionado à sessão.",
            )

        elif participacao.estado == (
            EstadoParticipacaoFisioterapia.CANCELADO
        ):
            participacao.alterar_estado(
                novo_estado=(
                    EstadoParticipacaoFisioterapia.AGENDADO
                ),
                utilizador=utilizador,
                motivo="Utente novamente adicionado à sessão.",
            )

    for utente_id, participacao in (
        participacoes_existentes.items()
    ):
        if (
            utente_id not in ids_selecionados
            and participacao.estado
            == EstadoParticipacaoFisioterapia.AGENDADO
        ):
            participacao.alterar_estado(
                novo_estado=(
                    EstadoParticipacaoFisioterapia.CANCELADO
                ),
                utilizador=utilizador,
                motivo="Utente retirado da sessão.",
            )

    atualizar_estado_sessao(sessao)


@transaction.atomic
def alterar_estado_participacao(
    participacao,
    novo_estado,
    utilizador,
    motivo="",
):
    """
    Altera o estado de um participante e recalcula
    automaticamente o estado geral da sessão.
    """
    if (
        novo_estado
        == EstadoParticipacaoFisioterapia.AGENDADO
        and participacao.utente.data_saida
    ):
        raise ValidationError(
            "Não é possível reagendar um utente com alta."
        )

    participacao.alterar_estado(
        novo_estado=novo_estado,
        utilizador=utilizador,
        motivo=motivo,
    )

    atualizar_estado_sessao(
        participacao.sessao
    )


@transaction.atomic
def cancelar_sessao(
    sessao,
    utilizador,
    motivo,
):
    """
    Cancela todos os participantes ainda agendados.

    Presenças já validadas como realizadas ou faltas
    não são alteradas.
    """
    participacoes = (
        sessao.participacoes
        .select_for_update()
        .filter(
            estado=(
                EstadoParticipacaoFisioterapia.AGENDADO
            )
        )
    )

    for participacao in participacoes:
        participacao.alterar_estado(
            novo_estado=(
                EstadoParticipacaoFisioterapia.CANCELADO
            ),
            profissional=utilizador,
            motivo=motivo,
        )

    atualizar_estado_sessao(sessao)