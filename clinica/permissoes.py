from django.db.models import Q

from .models import (
    AreaClinica,
    VisibilidadeRegistoClinico,
)


def obter_area_clinica(codigo):
    try:
        return (
            AreaClinica.objects
            .prefetch_related(
                "grupos_responsaveis",
                "grupos_partilha_geral",
            )
            .get(
                codigo=codigo,
                ativa=True,
            )
        )
    except AreaClinica.DoesNotExist:
        return None


def ids_grupos_utilizador(utilizador):
    if (
        not utilizador
        or not utilizador.is_authenticated
    ):
        return set()

    return set(
        utilizador.groups.values_list(
            "pk",
            flat=True,
        )
    )


def utilizador_e_responsavel_area(
    utilizador,
    codigo_area,
):
    area = obter_area_clinica(codigo_area)

    if not area:
        return False

    grupos_utilizador = ids_grupos_utilizador(
        utilizador
    )

    return area.grupos_responsaveis.filter(
        pk__in=grupos_utilizador,
    ).exists()


def utilizador_tem_acesso_area(
    utilizador,
    codigo_area,
):
    area = obter_area_clinica(codigo_area)

    if not area:
        return False

    grupos_utilizador = ids_grupos_utilizador(
        utilizador
    )

    return (
        area.grupos_responsaveis.filter(
            pk__in=grupos_utilizador,
        ).exists()
        or area.grupos_partilha_geral.filter(
            pk__in=grupos_utilizador,
        ).exists()
    )


def utilizador_pode_ver_registo(
    utilizador,
    registo,
    codigo_area,
):
    if (
        not utilizador
        or not utilizador.is_authenticated
    ):
        return False

    if registo.profissional_id == utilizador.pk:
        return True

    area = obter_area_clinica(codigo_area)

    if not area:
        return False

    grupos_utilizador = ids_grupos_utilizador(
        utilizador
    )

    pertence_area = area.grupos_responsaveis.filter(
        pk__in=grupos_utilizador,
    ).exists()

    tem_acesso_geral = (
        area.grupos_partilha_geral.filter(
            pk__in=grupos_utilizador,
        ).exists()
    )

    if (
        registo.visibilidade
        == VisibilidadeRegistoClinico.CONFIDENCIAL
    ):
        return False

    if (
        registo.visibilidade
        == VisibilidadeRegistoClinico.GRUPO
    ):
        return pertence_area

    if (
        registo.visibilidade
        == VisibilidadeRegistoClinico.TODOS
    ):
        return pertence_area or tem_acesso_geral

    return False


def utilizador_pode_editar_registo(
    utilizador,
    registo,
    codigo_area,
):
    if (
        not utilizador
        or not utilizador.is_authenticated
    ):
        return False

    if registo.profissional_id != utilizador.pk:
        return False

    return utilizador_e_responsavel_area(
        utilizador,
        codigo_area,
    )


def filtrar_registos_visiveis(
    queryset,
    utilizador,
    codigo_area,
    campo_autor="profissional_id",
    campo_visibilidade="visibilidade",
):
    if (
        not utilizador
        or not utilizador.is_authenticated
    ):
        return queryset.none()

    area = obter_area_clinica(codigo_area)

    if not area:
        return queryset.none()

    grupos_utilizador = ids_grupos_utilizador(
        utilizador
    )

    pertence_area = area.grupos_responsaveis.filter(
        pk__in=grupos_utilizador,
    ).exists()

    tem_acesso_geral = (
        area.grupos_partilha_geral.filter(
            pk__in=grupos_utilizador,
        ).exists()
    )

    condicao = Q(
        **{
            campo_autor: utilizador.pk,
        }
    )

    if pertence_area:
        condicao |= Q(
            **{
                campo_visibilidade: (
                    VisibilidadeRegistoClinico.GRUPO
                )
            }
        )

    if pertence_area or tem_acesso_geral:
        condicao |= Q(
            **{
                campo_visibilidade: (
                    VisibilidadeRegistoClinico.TODOS
                )
            }
        )

    return queryset.filter(condicao).distinct()