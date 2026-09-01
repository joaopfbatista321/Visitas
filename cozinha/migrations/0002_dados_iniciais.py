from django.db import migrations


def configurar_dados_iniciais(apps, schema_editor):
    UnidadeCozinha = apps.get_model(
        "cozinha",
        "UnidadeCozinha",
    )
    ProdutoCozinha = apps.get_model(
        "cozinha",
        "ProdutoCozinha",
    )
    TipoRefeicao = apps.get_model(
        "cozinha",
        "TipoRefeicao",
    )
    TipoDieta = apps.get_model(
        "cozinha",
        "TipoDieta",
    )

    UnidadeCozinha.objects.update_or_create(
        codigo="uldm",
        defaults={
            "nome": "ULDM",
            "ativa": True,
            "ordem": 10,
        },
    )

    tipos_refeicao = [
        (
            "pequeno-almoco",
            "Pequeno-almoço",
            10,
        ),
        (
            "meio-da-manha",
            "Meio da manhã",
            20,
        ),
        (
            "almoco",
            "Almoço",
            30,
        ),
        (
            "lanche",
            "Lanche",
            40,
        ),
        (
            "jantar",
            "Jantar",
            50,
        ),
        (
            "ceia",
            "Ceia",
            60,
        ),
    ]

    for codigo, nome, ordem in tipos_refeicao:
        TipoRefeicao.objects.update_or_create(
            codigo=codigo,
            defaults={
                "nome": nome,
                "ativo": True,
                "ordem": ordem,
            },
        )

    TipoDieta.objects.update_or_create(
        codigo="geral",
        defaults={
            "nome": "Geral",
            "descricao": (
                "Dieta geral. Os restantes tipos de dieta "
                "devem ser configurados no Django Admin."
            ),
            "ativo": True,
            "ordem": 10,
        },
    )

    produtos = [
        (
            "agua-033",
            "Água 0,33 L",
            "AGUA",
            "GAR",
        ),
        (
            "agua-15",
            "Água 1,5 L",
            "AGUA",
            "GAR",
        ),
        (
            "bolacha-agua-sal",
            "Bolacha Água e Sal",
            "BOLACHA",
            "UN",
        ),
        (
            "bolacha-integral",
            "Bolacha Integral",
            "BOLACHA",
            "UN",
        ),
        (
            "bolacha-maria",
            "Bolacha Maria",
            "BOLACHA",
            "UN",
        ),
        (
            "cha-saqueta",
            "Chá — saqueta",
            "BEBIDA",
            "UN",
        ),
        (
            "farinha-lactea-com-gluten",
            "Farinha láctea com glúten",
            "PAPA_FARINHA",
            "UN",
        ),
        (
            "farinha-lactea-sem-gluten",
            "Farinha láctea sem glúten",
            "PAPA_FARINHA",
            "UN",
        ),
        (
            "doce-di",
            "Doce DI",
            "SOPA_SOBREMESA",
            "POR",
        ),
        (
            "fruta-peca",
            "Fruta — peça",
            "SOPA_SOBREMESA",
            "UN",
        ),
        (
            "iogurte-aroma-normal",
            "Iogurte de aroma normal",
            "LACTICINIO",
            "UN",
        ),
        (
            "iogurte-aroma-magro",
            "Iogurte de aroma magro",
            "LACTICINIO",
            "UN",
        ),
        (
            "iogurte-liquido-normal",
            "Iogurte líquido normal",
            "LACTICINIO",
            "UN",
        ),
        (
            "iogurte-liquido-magro",
            "Iogurte líquido magro",
            "LACTICINIO",
            "UN",
        ),
        (
            "iogurte-natural",
            "Iogurte natural",
            "LACTICINIO",
            "UN",
        ),
        (
            "leite-litro",
            "Leite — litro",
            "LACTICINIO",
            "L",
        ),
        (
            "leite-di",
            "Leite DI",
            "LACTICINIO",
            "UN",
        ),
        (
            "manteiga-di",
            "Manteiga DI",
            "LACTICINIO",
            "UN",
        ),
        (
            "manteiga-sem-sal-di",
            "Manteiga sem sal DI",
            "LACTICINIO",
            "UN",
        ),
        (
            "pao",
            "Pão",
            "PAO_SANDES",
            "UN",
        ),
        (
            "queijo",
            "Queijo",
            "LACTICINIO",
            "UN",
        ),
        (
            "sandes-fiambre",
            "Sandes de fiambre",
            "PAO_SANDES",
            "UN",
        ),
        (
            "sandes-mista",
            "Sandes mista",
            "PAO_SANDES",
            "UN",
        ),
        (
            "sandes-queijo",
            "Sandes de queijo",
            "PAO_SANDES",
            "UN",
        ),
        (
            "sobremesa",
            "Sobremesa",
            "SOPA_SOBREMESA",
            "POR",
        ),
        (
            "sopa-legumes",
            "Sopa de legumes",
            "SOPA_SOBREMESA",
            "POR",
        ),
        (
            "sopa-enriquecida",
            "Sopa enriquecida",
            "SOPA_SOBREMESA",
            "POR",
        ),
        (
            "sumo-laranja-natural",
            "Sumo de laranja natural",
            "BEBIDA",
            "UN",
        ),
        (
            "sumo-nectar",
            "Sumo néctar",
            "BEBIDA",
            "UN",
        ),
        (
            "colheres",
            "Colheres",
            "CONSUMIVEL",
            "UN",
        ),
        (
            "tacas",
            "Taças",
            "CONSUMIVEL",
            "UN",
        ),
    ]

    for ordem, produto in enumerate(
        produtos,
        start=10,
    ):
        codigo, nome, categoria, unidade = produto

        ProdutoCozinha.objects.update_or_create(
            codigo=codigo,
            defaults={
                "nome": nome,
                "categoria": categoria,
                "unidade_medida": unidade,
                "ativo": True,
                "ordem": ordem,
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ("cozinha", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            configurar_dados_iniciais,
            migrations.RunPython.noop,
        ),
    ]
