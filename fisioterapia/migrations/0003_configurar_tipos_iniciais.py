import unicodedata

from django.db import migrations


TIPOS_INICIAIS = [
    {
        "nome": "Avaliação funcional",
        "categoria": "AVALIACAO",
        "descricao": (
            "Avaliação inicial ou periódica da capacidade "
            "funcional do utente."
        ),
        "ordem": 10,
        "ativo": True,
    },
    {
        "nome": "Fisioterapia motora",
        "categoria": "FISIOTERAPIA",
        "descricao": (
            "Intervenção dirigida à função motora, mobilidade "
            "e controlo do movimento."
        ),
        "ordem": 20,
        "ativo": True,
    },
    {
        "nome": "Fisioterapia respiratória",
        "categoria": "FISIOTERAPIA",
        "descricao": (
            "Técnicas respiratórias, expansão pulmonar, "
            "drenagem e higiene brônquica."
        ),
        "ordem": 30,
        "ativo": True,
    },
    {
        "nome": "Mobilização articular",
        "categoria": "FISIOTERAPIA",
        "descricao": (
            "Mobilização ativa, ativa-assistida ou passiva."
        ),
        "ordem": 40,
        "ativo": True,
    },
    {
        "nome": "Fortalecimento muscular",
        "categoria": "FISIOTERAPIA",
        "descricao": (
            "Exercícios destinados a melhorar a força "
            "e resistência muscular."
        ),
        "ordem": 50,
        "ativo": True,
    },
    {
        "nome": "Controlo da dor",
        "categoria": "FISIOTERAPIA",
        "descricao": (
            "Intervenções destinadas à redução e controlo "
            "da dor."
        ),
        "ordem": 60,
        "ativo": True,
    },
    {
        "nome": "Reabilitação funcional",
        "categoria": "REABILITACAO",
        "descricao": (
            "Recuperação ou manutenção da autonomia "
            "e capacidade funcional."
        ),
        "ordem": 70,
        "ativo": True,
    },
    {
        "nome": "Reabilitação neurológica",
        "categoria": "REABILITACAO",
        "descricao": (
            "Intervenção em alterações funcionais "
            "de origem neurológica."
        ),
        "ordem": 80,
        "ativo": True,
    },
    {
        "nome": "Reabilitação pós-operatória",
        "categoria": "REABILITACAO",
        "descricao": (
            "Reabilitação e recuperação funcional "
            "após intervenção cirúrgica."
        ),
        "ordem": 90,
        "ativo": True,
    },
    {
        "nome": "Treino de marcha",
        "categoria": "TREINO_FUNCIONAL",
        "descricao": (
            "Treino de marcha com ou sem produtos de apoio."
        ),
        "ordem": 100,
        "ativo": True,
    },
    {
        "nome": "Equilíbrio e coordenação",
        "categoria": "TREINO_FUNCIONAL",
        "descricao": (
            "Exercícios de equilíbrio, coordenação "
            "e controlo postural."
        ),
        "ordem": 110,
        "ativo": True,
    },
    {
        "nome": "Posicionamentos e transferências",
        "categoria": "TREINO_FUNCIONAL",
        "descricao": (
            "Treino de posicionamentos, levante, sentar "
            "e transferências."
        ),
        "ordem": 120,
        "ativo": True,
    },
    {
        "nome": "Prevenção de quedas",
        "categoria": "TREINO_FUNCIONAL",
        "descricao": (
            "Intervenção para redução do risco de queda."
        ),
        "ordem": 130,
        "ativo": True,
    },
    {
        "nome": "Outra intervenção",
        "categoria": "OUTRO",
        "descricao": (
            "Outra intervenção de fisioterapia "
            "ou reabilitação."
        ),
        "ordem": 900,
        "ativo": True,
    },
    {
        "nome": "Fisioterapia/Reabilitação (histórico)",
        "categoria": "OUTRO",
        "descricao": (
            "Tipo atribuído automaticamente a registos "
            "antigos sem classificação estruturada."
        ),
        "ordem": 999,
        "ativo": False,
    },
]


REGRAS_CLASSIFICACAO = [
    (
        (
            "avaliacao",
            "avaliar",
            "avaliado",
        ),
        "Avaliação funcional",
    ),
    (
        (
            "respiratorio",
            "respiratoria",
            "respiracao",
            "pulmonar",
            "bronquica",
            "bronquico",
        ),
        "Fisioterapia respiratória",
    ),
    (
        (
            "neurologico",
            "neurologica",
            "neurologia",
            "avc",
        ),
        "Reabilitação neurológica",
    ),
    (
        (
            "pos operatorio",
            "pos-operatorio",
            "pos cirurgico",
            "pos-cirurgico",
        ),
        "Reabilitação pós-operatória",
    ),
    (
        (
            "marcha",
            "andar",
            "deambulacao",
        ),
        "Treino de marcha",
    ),
    (
        (
            "equilibrio",
            "coordenacao",
            "controlo postural",
            "controle postural",
        ),
        "Equilíbrio e coordenação",
    ),
    (
        (
            "mobilizacao articular",
            "mobilizar articulacao",
            "amplitude articular",
        ),
        "Mobilização articular",
    ),
    (
        (
            "fortalecimento",
            "forca muscular",
            "resistencia muscular",
        ),
        "Fortalecimento muscular",
    ),
    (
        (
            "posicionamento",
            "transferencia",
            "levante",
        ),
        "Posicionamentos e transferências",
    ),
    (
        (
            "queda",
            "quedas",
            "risco de queda",
        ),
        "Prevenção de quedas",
    ),
    (
        (
            "dor",
            "analgesia",
            "doloroso",
        ),
        "Controlo da dor",
    ),
    (
        (
            "motora",
            "motor",
            "mobilidade",
            "movimento",
        ),
        "Fisioterapia motora",
    ),
]


def normalizar_texto(valor):
    valor = valor or ""

    valor = unicodedata.normalize(
        "NFKD",
        valor,
    )

    valor = "".join(
        caracter
        for caracter in valor
        if not unicodedata.combining(caracter)
    )

    return valor.lower().strip()


def encontrar_tipos(texto, tipos_por_nome):
    texto_normalizado = normalizar_texto(texto)
    tipos_encontrados = []

    for palavras, nome_tipo in REGRAS_CLASSIFICACAO:
        if any(
            palavra in texto_normalizado
            for palavra in palavras
        ):
            tipo = tipos_por_nome.get(nome_tipo)

            if (
                tipo
                and tipo.pk not in {
                    item.pk
                    for item in tipos_encontrados
                }
            ):
                tipos_encontrados.append(tipo)

    if (
        not tipos_encontrados
        and "reabilitacao" in texto_normalizado
    ):
        tipo = tipos_por_nome.get(
            "Reabilitação funcional"
        )

        if tipo:
            tipos_encontrados.append(tipo)

    if (
        not tipos_encontrados
        and "fisioterapia" in texto_normalizado
    ):
        tipo = tipos_por_nome.get(
            "Fisioterapia motora"
        )

        if tipo:
            tipos_encontrados.append(tipo)

    return tipos_encontrados


def configurar_tipos_iniciais(apps, schema_editor):
    TipoIntervencao = apps.get_model(
        "fisioterapia",
        "TipoIntervencaoFisioterapia",
    )

    Sessao = apps.get_model(
        "fisioterapia",
        "SessaoFisioterapia",
    )

    Registo = apps.get_model(
        "fisioterapia",
        "RegistoFisioterapia",
    )

    tipos_por_nome = {}

    for dados in TIPOS_INICIAIS:
        tipo, _ = TipoIntervencao.objects.update_or_create(
            nome=dados["nome"],
            defaults={
                "categoria": dados["categoria"],
                "descricao": dados["descricao"],
                "ordem": dados["ordem"],
                "ativo": dados["ativo"],
            },
        )

        tipos_por_nome[tipo.nome] = tipo

    tipo_historico = tipos_por_nome[
        "Fisioterapia/Reabilitação (histórico)"
    ]

    for sessao in Sessao.objects.all().iterator():
        campos_atualizar = []

        if (
            sessao.criado_por_id is None
            and sessao.profissional_id
        ):
            sessao.criado_por_id = sessao.profissional_id
            campos_atualizar.append("criado_por")

        local_normalizado = normalizar_texto(
            sessao.local
        )

        if any(
            palavra in local_normalizado
            for palavra in (
                "leito",
                "quarto",
                "cama",
            )
        ):
            sessao.local_realizacao = "LEITO"
            campos_atualizar.append(
                "local_realizacao"
            )

        elif any(
            palavra in local_normalizado
            for palavra in (
                "reabilitacao",
                "ginasio",
                "fisioterapia",
            )
        ):
            sessao.local_realizacao = (
                "SALA_REABILITACAO"
            )
            campos_atualizar.append(
                "local_realizacao"
            )

        elif local_normalizado:
            sessao.local_realizacao = "OUTRO"
            campos_atualizar.append(
                "local_realizacao"
            )

        if campos_atualizar:
            sessao.save(
                update_fields=list(
                    set(campos_atualizar)
                )
            )

        if not sessao.tipos_intervencao.exists():
            texto_sessao = " ".join([
                sessao.trabalho_planeado or "",
                sessao.observacoes or "",
            ])

            tipos_encontrados = encontrar_tipos(
                texto_sessao,
                tipos_por_nome,
            )

            if tipos_encontrados:
                sessao.tipos_intervencao.add(
                    *tipos_encontrados
                )
            else:
                sessao.tipos_intervencao.add(
                    tipo_historico
                )

    for registo in Registo.objects.all().iterator():
        if registo.tipos_intervencao.exists():
            continue

        texto_registo = " ".join([
            registo.tipo_trabalho or "",
            registo.trabalho_realizado or "",
            registo.resposta_utente or "",
            registo.plano_seguinte or "",
        ])

        tipos_encontrados = encontrar_tipos(
            texto_registo,
            tipos_por_nome,
        )

        if tipos_encontrados:
            registo.tipos_intervencao.add(
                *tipos_encontrados
            )
        else:
            registo.tipos_intervencao.add(
                tipo_historico
            )


class Migration(migrations.Migration):

    dependencies = [
        (
            "fisioterapia",
            "0002_tipointervencaofisioterapia_and_more",
        ),
    ]

    operations = [
        migrations.RunPython(
            configurar_tipos_iniciais,
            reverse_code=migrations.RunPython.noop,
        ),
    ]