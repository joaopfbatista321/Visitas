from django.db import migrations


GRUPOS_CLINICOS = [
    "UCCI_Enfermagem",
    "UCCI_Medicos",
    "UCCI_Psicologia",
    "UCCI_Fisioterapia",
    "UCCI_ServicoSocial",
]


AREAS_CLINICAS = [
    {
        "codigo": "enfermagem",
        "nome": "Enfermagem",
        "descricao": (
            "Registos de Enfermagem, avaliações, "
            "cuidados e ocorrências clínicas."
        ),
        "grupo_responsavel": "UCCI_Enfermagem",
    },
    {
        "codigo": "medicos",
        "nome": "Área Médica",
        "descricao": (
            "Observações, avaliações e registos médicos."
        ),
        "grupo_responsavel": "UCCI_Medicos",
    },
    {
        "codigo": "psicologia",
        "nome": "Psicologia",
        "descricao": (
            "Avaliação e acompanhamento psicológico."
        ),
        "grupo_responsavel": "UCCI_Psicologia",
    },
    {
        "codigo": "fisioterapia",
        "nome": "Fisioterapia",
        "descricao": (
            "Reabilitação e acompanhamento funcional."
        ),
        "grupo_responsavel": "UCCI_Fisioterapia",
    },
    {
        "codigo": "servico-social",
        "nome": "Serviço Social",
        "descricao": (
            "Avaliação e acompanhamento social."
        ),
        "grupo_responsavel": "UCCI_ServicoSocial",
    },
]


def configurar_areas_clinicas(apps, schema_editor):
    Group = apps.get_model(
        "auth",
        "Group",
    )

    AreaClinica = apps.get_model(
        "clinica",
        "AreaClinica",
    )

    grupos = {}

    for nome_grupo in GRUPOS_CLINICOS:
        grupo, _ = Group.objects.get_or_create(
            name=nome_grupo,
        )

        grupos[nome_grupo] = grupo

    grupos_partilha = [
        grupos[nome_grupo]
        for nome_grupo in GRUPOS_CLINICOS
    ]

    for configuracao in AREAS_CLINICAS:
        area, _ = AreaClinica.objects.update_or_create(
            codigo=configuracao["codigo"],
            defaults={
                "nome": configuracao["nome"],
                "descricao": configuracao["descricao"],
                "ativa": True,
            },
        )

        grupo_responsavel = grupos[
            configuracao["grupo_responsavel"]
        ]

        area.grupos_responsaveis.set(
            [grupo_responsavel]
        )

        area.grupos_partilha_geral.set(
            grupos_partilha
        )


def remover_areas_clinicas(apps, schema_editor):
    AreaClinica = apps.get_model(
        "clinica",
        "AreaClinica",
    )

    codigos = [
        configuracao["codigo"]
        for configuracao in AREAS_CLINICAS
    ]

    AreaClinica.objects.filter(
        codigo__in=codigos
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        (
            "clinica",
            "0001_initial",
        ),
    ]

    operations = [
        migrations.RunPython(
            configurar_areas_clinicas,
            remover_areas_clinicas,
        ),
    ]