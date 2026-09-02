from datetime import date, timedelta

from django.db.models import Q, Sum
from django.utils import timezone

from enfermagem.models import AusenciaUtente, EstadoAusenciaUtente

from .models import Piso, Quarto, Utente


def _data_local(valor):
    if valor is None:
        return None
    if timezone.is_aware(valor):
        return timezone.localtime(valor).date()
    return valor.date()


def _datas(inicio, fim):
    atual = inicio
    while atual < fim:
        yield atual
        atual += timedelta(days=1)


def resolver_periodo(tipo, referencia):
    if tipo == "semana":
        inicio = referencia - timedelta(days=referencia.weekday())
        return inicio, inicio + timedelta(days=7)

    if tipo == "mes":
        inicio = referencia.replace(day=1)
        if inicio.month == 12:
            fim = date(inicio.year + 1, 1, 1)
        else:
            fim = date(inicio.year, inicio.month + 1, 1)
        return inicio, fim

    return referencia, referencia + timedelta(days=1)


def calcular_mapa_ocupacao(inicio, fim, piso=""):
    pisos = [
        (codigo, nome)
        for codigo, nome in Piso.choices
        if not piso or codigo == piso
    ]
    codigos_piso = [codigo for codigo, _ in pisos]

    capacidades = {
        linha["piso"]: linha["total"] or 0
        for linha in (
            Quarto.objects.filter(piso__in=codigos_piso)
            .values("piso")
            .annotate(total=Sum("capacidade"))
        )
    }

    utentes = list(
        Utente.objects.filter(
            quarto__piso__in=codigos_piso,
            data_entrada__lt=fim,
        )
        .filter(Q(data_saida__isnull=True) | Q(data_saida__gt=inicio))
        .select_related("quarto")
    )

    ids_utentes = [utente.pk for utente in utentes]
    ausencias_por_utente = {}

    if ids_utentes:
        ausencias = (
            AusenciaUtente.objects.filter(
                utente_id__in=ids_utentes,
                data_hora_inicio__date__lt=fim,
            )
            .exclude(estado=EstadoAusenciaUtente.CANCELADA)
            .filter(
                Q(data_hora_regresso__isnull=True)
                | Q(data_hora_regresso__date__gt=inicio)
            )
        )

        for ausencia in ausencias:
            ausencias_por_utente.setdefault(ausencia.utente_id, []).append(
                (
                    _data_local(ausencia.data_hora_inicio),
                    _data_local(ausencia.data_hora_regresso),
                )
            )

    datas = list(_datas(inicio, fim))
    linhas = []

    for codigo, nome in pisos:
        capacidade = capacidades.get(codigo, 0)
        utentes_piso = [
            utente for utente in utentes if utente.quarto.piso == codigo
        ]
        ocupacao_camas_dia = 0
        presenca_camas_dia = 0

        for dia in datas:
            internados = [
                utente
                for utente in utentes_piso
                if utente.data_entrada <= dia
                and (utente.data_saida is None or utente.data_saida > dia)
            ]
            ocupacao_camas_dia += len(internados)

            for utente in internados:
                esta_ausente = any(
                    inicio_ausencia <= dia
                    and (fim_ausencia is None or dia < fim_ausencia)
                    for inicio_ausencia, fim_ausencia in (
                        ausencias_por_utente.get(utente.pk, [])
                    )
                )
                if not esta_ausente:
                    presenca_camas_dia += 1

        camas_dia_disponiveis = capacidade * len(datas)
        taxa_ocupacao = (
            ocupacao_camas_dia * 100 / camas_dia_disponiveis
            if camas_dia_disponiveis
            else None
        )
        taxa_presenca = (
            presenca_camas_dia * 100 / camas_dia_disponiveis
            if camas_dia_disponiveis
            else None
        )

        linhas.append(
            {
                "piso_codigo": codigo,
                "piso_nome": nome,
                "capacidade": capacidade,
                "dias_periodo": len(datas),
                "camas_dia_disponiveis": camas_dia_disponiveis,
                "ocupacao_camas_dia": ocupacao_camas_dia,
                "presenca_camas_dia": presenca_camas_dia,
                "taxa_ocupacao": taxa_ocupacao,
                "taxa_presenca": taxa_presenca,
            }
        )

    total_disponivel = sum(
        linha["camas_dia_disponiveis"] for linha in linhas
    )
    total_ocupado = sum(linha["ocupacao_camas_dia"] for linha in linhas)
    total_presente = sum(linha["presenca_camas_dia"] for linha in linhas)

    total = {
        "capacidade": sum(linha["capacidade"] for linha in linhas),
        "camas_dia_disponiveis": total_disponivel,
        "ocupacao_camas_dia": total_ocupado,
        "presenca_camas_dia": total_presente,
        "taxa_ocupacao": (
            total_ocupado * 100 / total_disponivel
            if total_disponivel
            else None
        ),
        "taxa_presenca": (
            total_presente * 100 / total_disponivel
            if total_disponivel
            else None
        ),
    }

    return linhas, total
