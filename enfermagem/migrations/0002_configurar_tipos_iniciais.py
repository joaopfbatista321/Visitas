from django.db import migrations


TIPOS_INICIAIS = [
    {
        "codigo": "evolucao-enfermagem",
        "nome": "Evolução de Enfermagem",
        "descricao": (
            "Registo da evolução clínica e do estado "
            "geral do utente."
        ),
        "ordem": 10,
    },
    {
        "codigo": "avaliacao-clinica",
        "nome": "Avaliação de Enfermagem",
        "descricao": (
            "Avaliação clínica realizada pela equipa "
            "de Enfermagem."
        ),
        "ordem": 20,
    },
    {
        "codigo": "cuidados-prestados",
        "nome": "Cuidados prestados",
        "descricao": (
            "Registo dos cuidados e intervenções "
            "realizadas ao utente."
        ),
        "ordem": 30,
    },
    {
        "codigo": "feridas-pensos",
        "nome": "Feridas e pensos",
        "descricao": (
            "Avaliação de feridas, realização de pensos "
            "e respetiva evolução."
        ),
        "ordem": 40,
    },
    {
        "codigo": "controlo-dor",
        "nome": "Avaliação e controlo da dor",
        "descricao": (
            "Avaliação da dor, medidas adotadas "
            "e resposta do utente."
        ),
        "ordem": 50,
    },
    {
        "codigo": "alimentacao-hidratacao",
        "nome": "Alimentação e hidratação",
        "descricao": (
            "Registo relacionado com alimentação, "
            "hidratação e tolerância."
        ),
        "ordem": 60,
    },
    {
        "codigo": "eliminacao",
        "nome": "Eliminação",
        "descricao": (
            "Registo de informação relacionada com "
            "eliminação urinária ou intestinal."
        ),
        "ordem": 70,
    },
    {
        "codigo": "ocorrencia",
        "nome": "Ocorrência de Enfermagem",
        "descricao": (
            "Registo de uma ocorrência ou situação "
            "relevante não abrangida por outro tipo."
        ),
        "ordem": 80,
    },
    {
        "codigo": "queda",
        "nome": "Registo de queda",
        "descricao": (
            "Registo estruturado de uma queda do utente."
        ),
        "ordem": 90,
    },
]


def configurar_tipos_iniciais(
    apps,
    schema_editor,
):
    TipoRegistoEnfermagem = apps.get_model(
        "enfermagem",
        "TipoRegistoEnfermagem",
    )

    for dados in TIPOS_INICIAIS:
        TipoRegistoEnfermagem.objects.update_or_create(
            codigo=dados["codigo"],
            defaults={
                "nome": dados["nome"],
                "descricao": dados["descricao"],
                "ordem": dados["ordem"],
                "ativo": True,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        (
            "enfermagem",
            "0001_initial",
        ),
    ]

    operations = [
        migrations.RunPython(
            configurar_tipos_iniciais,
            migrations.RunPython.noop,
        ),
    ]