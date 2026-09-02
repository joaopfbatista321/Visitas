from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone

from enfermagem.models import AusenciaUtente, EstadoAusenciaUtente

from .models import Mensalidade, PagamentoMensalidade, Utente


CENTIMOS = Decimal("0.01")


def intervalo_mes(ano, mes):
    inicio = date(ano, mes, 1)
    fim = inicio + timedelta(days=monthrange(ano, mes)[1])
    return inicio, fim


def _data_local(valor):
    if valor is None:
        return None
    if timezone.is_aware(valor):
        return timezone.localtime(valor).date()
    return valor.date()


def _dias_intervalo(inicio, fim):
    atual = inicio
    while atual < fim:
        yield atual
        atual += timedelta(days=1)


def calcular_dias_mensalidade(utente, ano, mes):
    """
    O dia de entrada é faturado e o dia da saída não é faturado.
    Quando o utente não paga ausências, o dia da saída temporária não
    conta e o dia do regresso volta a contar.
    """
    inicio_mes, fim_mes = intervalo_mes(ano, mes)
    inicio_estadia = max(utente.data_entrada, inicio_mes)
    fim_estadia = min(utente.data_saida or fim_mes, fim_mes)

    if fim_estadia <= inicio_estadia:
        return {
            "dias_estadia": 0,
            "dias_ausencia": 0,
            "dias_faturaveis": 0,
        }

    dias_estadia = set(_dias_intervalo(inicio_estadia, fim_estadia))
    dias_ausencia = set()

    if not utente.paga_dias_ausencia:
        ausencias = (
            AusenciaUtente.objects.filter(
                utente=utente,
                data_hora_inicio__date__lt=fim_estadia,
            )
            .exclude(estado=EstadoAusenciaUtente.CANCELADA)
            .filter(
                Q(data_hora_regresso__isnull=True)
                | Q(data_hora_regresso__date__gt=inicio_estadia)
            )
        )

        for ausencia in ausencias:
            inicio_ausencia = max(
                _data_local(ausencia.data_hora_inicio),
                inicio_estadia,
            )
            fim_ausencia = min(
                _data_local(ausencia.data_hora_regresso) or fim_estadia,
                fim_estadia,
            )

            if fim_ausencia > inicio_ausencia:
                dias_ausencia.update(
                    _dias_intervalo(inicio_ausencia, fim_ausencia)
                )

    dias_ausencia.intersection_update(dias_estadia)

    return {
        "dias_estadia": len(dias_estadia),
        "dias_ausencia": len(dias_ausencia),
        "dias_faturaveis": len(dias_estadia - dias_ausencia),
    }


def calcular_valores_mensalidade(utente, ano, mes):
    dias = calcular_dias_mensalidade(utente, ano, mes)
    valor_dia = utente.valor_dia or Decimal("0.00")
    valor_total = (
        valor_dia * dias["dias_faturaveis"]
    ).quantize(CENTIMOS)

    return {
        **dias,
        "valor_dia": valor_dia,
        "valor_total": valor_total,
    }


@transaction.atomic
def gerar_mensalidades(ano, mes):
    """
    Cria ou recalcula as mensalidades dos utentes presentes no mês.

    Este processo não cria movimentos na conta pessoal nem altera o saldo
    disponível do utente.
    """
    inicio_mes, fim_mes = intervalo_mes(ano, mes)
    utentes = (
        Utente.objects.filter(data_entrada__lt=fim_mes)
        .filter(Q(data_saida__isnull=True) | Q(data_saida__gt=inicio_mes))
        .order_by("pk")
    )

    resultado = {"criadas": 0, "atualizadas": 0, "reabertas": 0}

    for utente in utentes:
        valores = calcular_valores_mensalidade(utente, ano, mes)
        mensalidade, criada = Mensalidade.objects.get_or_create(
            utente=utente,
            ano=ano,
            mes=mes,
            defaults=valores,
        )

        if criada:
            resultado["criadas"] += 1
            continue

        alterou = any(
            getattr(mensalidade, campo) != valor
            for campo, valor in valores.items()
        )
        if not alterou:
            continue

        total_recebido = mensalidade.pagamentos.aggregate(
            total=Sum("valor")
        )["total"] or Decimal("0.00")
        if total_recebido == 0 and mensalidade.pago:
            total_recebido = mensalidade.valor_total
        tinha_pagamentos = total_recebido > 0

        for campo, valor in valores.items():
            setattr(mensalidade, campo, valor)

        mensalidade.pago = (
            mensalidade.valor_total > 0
            and total_recebido >= mensalidade.valor_total
        )
        if not mensalidade.pago:
            mensalidade.pago_em = None
            mensalidade.confirmado_por = None

        if tinha_pagamentos:
            mensalidade.necessita_revisao = True
            resultado["reabertas"] += 1
        else:
            resultado["atualizadas"] += 1

        mensalidade.full_clean()
        mensalidade.save()

    return resultado


@transaction.atomic
def registar_pagamento_mensalidade(
    mensalidade,
    valor,
    data_pagamento,
    utilizador,
    observacoes="",
):
    """
    Regista um recebimento da mensalidade no respetivo histórico.

    O recebimento é administrativo e nunca é debitado ou creditado na conta
    pessoal do utente.
    """
    mensalidade = Mensalidade.objects.select_for_update().get(
        pk=mensalidade.pk
    )

    valor = Decimal(valor).quantize(CENTIMOS)
    total_recebido = mensalidade.pagamentos.aggregate(
        total=Sum("valor")
    )["total"] or Decimal("0.00")
    if total_recebido == 0 and mensalidade.pago:
        total_recebido = mensalidade.valor_total

    valor_em_falta = max(
        mensalidade.valor_total - total_recebido,
        Decimal("0.00"),
    )

    if valor <= 0:
        raise ValidationError("O valor recebido tem de ser superior a zero.")
    if valor > valor_em_falta:
        raise ValidationError(
            f"O valor recebido não pode exceder os {valor_em_falta:.2f} € "
            "em falta."
        )

    pagamento = PagamentoMensalidade.objects.create(
        mensalidade=mensalidade,
        valor=valor,
        data_pagamento=data_pagamento or timezone.localdate(),
        observacoes=(observacoes or "").strip(),
        registado_por=utilizador,
    )

    novo_total_recebido = total_recebido + valor
    mensalidade.pago = novo_total_recebido >= mensalidade.valor_total
    mensalidade.necessita_revisao = False

    if mensalidade.pago:
        mensalidade.pago_em = timezone.now()
        mensalidade.confirmado_por = utilizador
    else:
        mensalidade.pago_em = None
        mensalidade.confirmado_por = None

    mensalidade.full_clean()
    mensalidade.save(
        update_fields=[
            "pago",
            "pago_em",
            "confirmado_por",
            "necessita_revisao",
            "atualizado_em",
        ]
    )
    return pagamento
