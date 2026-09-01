from datetime import datetime, time

from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from visitas.models import Utente

from .models import (
    EstadoParticipacaoFisioterapia,
    EstadoSessaoFisioterapia,
    ParticipacaoFisioterapia,
    SessaoFisioterapia,
)


@receiver(post_save, sender=Utente)
def cancelar_fisioterapia_apos_alta(
    sender,
    instance,
    **kwargs,
):
    """
    Quando é registada a alta de um utente, cancela todas
    as suas participações futuras que ainda estavam agendadas.

    Os registos não são apagados, preservando o histórico.
    """
    if not instance.data_saida:
        return

    inicio_dia_alta = datetime.combine(
        instance.data_saida,
        time.min,
    )

    if settings.USE_TZ:
        inicio_dia_alta = timezone.make_aware(
            inicio_dia_alta,
            timezone.get_current_timezone(),
        )

    motivo = (
        "Cancelamento automático devido à alta do utente "
        f"em {instance.data_saida:%d/%m/%Y}."
    )

    with transaction.atomic():
        participacoes = list(
            ParticipacaoFisioterapia.objects
            .select_for_update()
            .select_related("sessao")
            .filter(
                utente=instance,
                estado=EstadoParticipacaoFisioterapia.AGENDADO,
                sessao__inicio__gte=inicio_dia_alta,
            )
        )

        sessoes_afetadas = set()

        for participacao in participacoes:
            sessoes_afetadas.add(
                participacao.sessao_id
            )

            participacao.alterar_estado(
                novo_estado=(
                    EstadoParticipacaoFisioterapia.CANCELADO_ALTA
                ),
                utilizador=None,
                motivo=motivo,
            )

        sessoes = SessaoFisioterapia.objects.filter(
            pk__in=sessoes_afetadas,
            estado=EstadoSessaoFisioterapia.AGENDADA,
        )

        estados_cancelados = {
            EstadoParticipacaoFisioterapia.CANCELADO,
            EstadoParticipacaoFisioterapia.CANCELADO_ALTA,
        }

        for sessao in sessoes:
            existe_participacao_nao_cancelada = (
                sessao.participacoes
                .exclude(estado__in=estados_cancelados)
                .exists()
            )

            if not existe_participacao_nao_cancelada:
                sessao.estado = (
                    EstadoSessaoFisioterapia.CANCELADA
                )

                sessao.save(
                    update_fields=[
                        "estado",
                        "atualizado_em",
                    ]
                )