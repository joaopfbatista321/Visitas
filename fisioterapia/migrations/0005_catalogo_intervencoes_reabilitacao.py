from django.db import migrations, models


INTERVENCOES = {
    "FISIOTERAPIA": [
        "Treino de equilíbrio",
        "Treino de coordenação",
        "Fortalecimento muscular",
        "Mobilização articular ativa-assistida",
        "Mobilização articular passiva",
        "Posicionamentos no leito",
        "Treino de marcha",
        "Treino de subir/descer escadas",
        "Agentes físicos",
        "Técnicas específicas de cinesioterapia",
        "Treino proprioceptivo",
        "Massagem manual",
        "Reeducação funcional",
        "Treino de transferências",
        "Técnicas de modelagem ao coto",
        "Outros",
    ],
    "TERAPIA_OCUPACIONAL": [
        "Mobilização articular ativa-assistida",
        "Mobilização articular passiva",
        "Reeducação do membro superior afetado",
        "Aconselhamento de estratégias de adaptação e produtos de apoio",
        "Promoção dos movimentos ativos do MS",
        "Promoção da coordenação motora do MS",
        "Promoção da força muscular do MS",
        "Atividades de amplitude articular da anca",
        "Atividades de amplitude de movimento do MS",
        "Atividades de motricidade global",
        "Atividades de motricidade fina",
        "Treino de escrita",
        "Treino de equilíbrio",
        "Atividades de atenção ao hemicorpo e hemiespaço",
        "Atividades para o neglect",
        "Estimulação sensorial",
        "Atividades de sentido de autoeficácia do utente",
        "Atividades para preservação das capacidades remanescentes do utente",
        "Ocupações significativas",
        "Sessões de relaxamento",
        "Treino de AVD",
        "Treino de AVDI",
        "Outros",
    ],
    "TERAPIA_FALA": [
        "Exercícios miofuncionais",
        "Mímica facial",
        "Exercícios isotónicos, isométricos e isocinéticos",
        "Tarefas de compreensão",
        "Tarefas de identificação",
        "Perguntas de resposta sim-não",
        "Perguntas de resposta geral",
        "Nomeação rápida por categorias",
        "Emparelhar imagem-palavra",
        "Tarefas de responsive-naming",
        "Tarefas de leitura e escrita",
        "Estimulação sensorial oral",
        "Exercícios de MOF",
        "Treino de deglutição",
        "Exercícios de respiração",
        "Exercícios de voz",
        "Outros",
    ],
}


def configurar_catalogo(apps, schema_editor):
    Grupo = apps.get_model("auth", "Group")
    TipoIntervencao = apps.get_model(
        "fisioterapia",
        "TipoIntervencaoFisioterapia",
    )

    for nome_grupo in (
        "UCCI_Fisioterapia",
        "UCCI_TerapiaOcupacional",
        "UCCI_TerapiaFala",
    ):
        Grupo.objects.get_or_create(name=nome_grupo)

    for area, nomes in INTERVENCOES.items():
        TipoIntervencao.objects.filter(
            area=area,
            ativo=True,
        ).exclude(nome__in=nomes).update(ativo=False)

        for posicao, nome in enumerate(nomes, start=1):
            categoria = (
                "OUTRO"
                if nome == "Outros"
                else (
                    "FISIOTERAPIA"
                    if area == "FISIOTERAPIA"
                    else "REABILITACAO"
                )
            )

            TipoIntervencao.objects.update_or_create(
                area=area,
                nome=nome,
                defaults={
                    "categoria": categoria,
                    "descricao": "",
                    "ativo": True,
                    "ordem": posicao * 10,
                },
            )


class Migration(migrations.Migration):
    dependencies = [
        (
            "fisioterapia",
            "0004_alter_registofisioterapia_options_and_more",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="tipointervencaofisioterapia",
            name="area",
            field=models.CharField(
                choices=[
                    ("FISIOTERAPIA", "Fisioterapia"),
                    (
                        "TERAPIA_OCUPACIONAL",
                        "Terapia Ocupacional",
                    ),
                    ("TERAPIA_FALA", "Terapia da Fala"),
                ],
                db_index=True,
                default="FISIOTERAPIA",
                max_length=30,
                verbose_name="Área de Reabilitação",
            ),
        ),
        migrations.AlterField(
            model_name="tipointervencaofisioterapia",
            name="nome",
            field=models.CharField(
                max_length=150,
                verbose_name="Designação",
            ),
        ),
        migrations.AlterModelOptions(
            name="tipointervencaofisioterapia",
            options={
                "ordering": [
                    "area",
                    "ordem",
                    "categoria",
                    "nome",
                ],
                "verbose_name": (
                    "Tipo de intervenção de reabilitação"
                ),
                "verbose_name_plural": (
                    "Tipos de intervenção de reabilitação"
                ),
            },
        ),
        migrations.AddConstraint(
            model_name="tipointervencaofisioterapia",
            constraint=models.UniqueConstraint(
                fields=("area", "nome"),
                name="reab_interv_area_nome_uniq",
            ),
        ),
        migrations.RunPython(
            configurar_catalogo,
            migrations.RunPython.noop,
        ),
    ]
