from django.db import models


GRUPOS_CLINICOS = (
    "UCCI_Enfermagem",
    "UCCI_Medicos",
    "UCCI_Psicologia",
    "UCCI_Fisioterapia",
    "UCCI_TerapiaOcupacional",
    "UCCI_TerapiaFala",
    "UCCI_ServicoSocial",
)


class VisibilidadeRegisto(models.TextChoices):
    CONFIDENCIAL = "CONFIDENCIAL", "Apenas eu"
    GRUPO = "GRUPO", "Grupo profissional"
    TODOS = "TODOS", "Todos os profissionais clínicos"


def pode_ver_registo(
    utilizador,
    autor_id,
    visibilidade,
    grupo_profissional,
):
    """
    Verifica se o utilizador pode consultar um registo clínico.

    CONFIDENCIAL:
        Apenas o autor.

    GRUPO:
        Autor e utilizadores do mesmo grupo profissional.

    TODOS:
        Apenas os grupos clínicos autorizados.
    """
    if not utilizador.is_authenticated:
        return False

    if utilizador.pk == autor_id:
        return True

    if visibilidade == VisibilidadeRegisto.CONFIDENCIAL:
        return False

    grupos_utilizador = set(
        utilizador.groups.values_list("name", flat=True)
    )

    if visibilidade == VisibilidadeRegisto.GRUPO:
        return grupo_profissional in grupos_utilizador

    if visibilidade == VisibilidadeRegisto.TODOS:
        return bool(
            grupos_utilizador.intersection(GRUPOS_CLINICOS)
        )

    return False


def pode_editar_registo(utilizador, autor_id):
    """
    Um registo clínico só pode ser alterado pelo respetivo autor.
    """
    return (
        utilizador.is_authenticated
        and utilizador.pk == autor_id
    )
