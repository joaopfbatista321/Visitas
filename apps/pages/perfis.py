"""Configuração das páginas iniciais de cada departamento da UCCI."""


PERFIS_PORTAL = {
    "UCCI_Rececao": {
        "slug": "rececao",
        "titulo": "Receção",
        "descricao": (
            "Gestão operacional, utentes, visitas "
            "e transportes."
        ),
        "icone": "clipboard",
        "cor": "primary",
    },

        "UCCI_Enfermagem": {
        "slug": "enfermagem",
        "titulo": "Enfermagem",
        "descricao": (
            "Registos clínicos, acompanhamento dos utentes, "
            "quedas, isolamentos e pedidos de transporte."
        ),
        "icone": "heart",
        "cor": "danger",
        "acessos": [
            {
                "titulo": "Utentes e registos",
                "descricao": (
                    "Consultar os utentes e aceder ao respetivo "
                    "histórico de Enfermagem."
                ),
                "icone": "users",
                "url": "visitas:lista_utentes",
            },
            {
                "titulo": "Registo de quedas",
                "descricao": (
                    "Consultar, pesquisar e acompanhar todas "
                    "as notificações de queda."
                ),
                "icone": "alert-triangle",
                "url": "enfermagem:lista_quedas",
            },
            {
                "titulo": "Isolamentos",
                "descricao": (
                    "Consultar e gerir os isolamentos ativos."
                ),
                "icone": "shield",
                "url": "visitas:isolamentos_ativos",
            },
            {
                "titulo": "Novo pedido de transporte",
                "descricao": (
                    "Enviar um pedido de transporte para "
                    "validação pela Receção."
                ),
                "icone": "plus-circle",
                "url": "visitas:criar_pedido_transporte",
            },
            {
                "titulo": "Pedidos de transporte",
                "descricao": (
                    "Acompanhar os pedidos e os respetivos estados."
                ),
                "icone": "truck",
                "url": "visitas:lista_pedidos_transporte",
            },

            {
                "titulo": "Novo pedido à Cozinha",
                "descricao": "Indicar refeições e suplementos do piso até às 12:00.",
                "icone": "coffee",
                "url": "cozinha:criar_pedido",
            },
            {
                "titulo": "Pedidos à Cozinha",
                "descricao": "Confirmar a receção e registar o consumo do piso.",
                "icone": "clipboard",
                "url": "cozinha:lista_pedidos",
            },
        ],
    },

    "UCCI_Medicos": {
        "slug": "medicos",
        "titulo": "Área Médica",
        "descricao": (
            "Informação clínica, isolamentos "
            "e pedidos de transporte."
        ),
        "icone": "activity",
        "cor": "success",
        "acessos": [
            {
                "titulo": "Utentes",
                "descricao": (
                    "Consultar a lista e a ficha dos utentes."
                ),
                "icone": "users",
                "url": "visitas:lista_utentes",
            },
            {
                "titulo": "Isolamentos",
                "descricao": (
                    "Consultar e gerir os isolamentos ativos."
                ),
                "icone": "shield",
                "url": "visitas:isolamentos_ativos",
            },
            {
                "titulo": "Novo pedido de transporte",
                "descricao": (
                    "Enviar um pedido para validação "
                    "pela Receção."
                ),
                "icone": "plus-circle",
                "url": "visitas:criar_pedido_transporte",
            },
            {
                "titulo": "Pedidos de transporte",
                "descricao": (
                    "Acompanhar todos os pedidos "
                    "e respetivos estados."
                ),
                "icone": "list",
                "url": "visitas:lista_pedidos_transporte",
            },
        ],
    },

    "UCCI_Psicologia": {
        "slug": "psicologia",
        "titulo": "Psicologia",
        "descricao": (
            "Avaliação e acompanhamento psicológico "
            "dos utentes."
        ),
        "icone": "message-circle",
        "cor": "info",
        "acessos": [
            {
                "titulo": "Utentes",
                "descricao": (
                    "Consultar a lista e a ficha dos utentes."
                ),
                "icone": "users",
                "url": "visitas:lista_utentes",
            },
        ],
    },

    "UCCI_ServicoSocial": {
        "slug": "servico-social",
        "titulo": "Serviço Social",
        "descricao": (
            "Acompanhamento social e articulação "
            "com entidades externas."
        ),
        "icone": "users",
        "cor": "info",
        "acessos": [
            {
                "titulo": "Utentes",
                "descricao": (
                    "Consultar a lista e a ficha dos utentes."
                ),
                "icone": "users",
                "url": "visitas:lista_utentes",
            },
            {
                "titulo": "Novo pedido de transporte",
                "descricao": (
                    "Enviar um pedido para validação "
                    "pela Receção."
                ),
                "icone": "plus-circle",
                "url": "visitas:criar_pedido_transporte",
            },
            {
                "titulo": "Pedidos de transporte",
                "descricao": (
                    "Acompanhar todos os pedidos "
                    "e respetivos estados."
                ),
                "icone": "list",
                "url": "visitas:lista_pedidos_transporte",
            },
        ],
    },

    "UCCI_Fisioterapia": {
        "slug": "fisioterapia",
        "titulo": "Fisioterapia",
        "descricao": (
            "Planeamento, realização e registo "
            "da reabilitação dos utentes."
        ),
        "icone": "activity",
        "cor": "warning",
        "acessos": [
            {
                "titulo": "Calendário",
                "descricao": (
                    "Consultar a agenda da equipa "
                    "de Fisioterapia."
                ),
                "icone": "calendar",
                "url": "fisioterapia:calendario",
            },
            {
                "titulo": "Alertas clínicos",
                "descricao": (
                    "Consultar quedas das últimas 24 horas "
                    "e isolamentos ativos."
                ),
                "icone": "alert-triangle",
                "url": "fisioterapia:alertas_clinicos",
            },
            {
                "titulo": "Nova sessão",
                "descricao": (
                    "Marcar uma sessão individual "
                    "ou de grupo."
                ),
                "icone": "plus-circle",
                "url": "fisioterapia:criar_sessao",
            },
            {
                "titulo": "Presenças por validar",
                "descricao": (
                    "Consultar sessões já iniciadas "
                    "com utentes ainda por validar."
                ),
                "icone": "check-square",
                "url": "fisioterapia:lista_sessoes",
                "query": "por_validar=1",
            },
            {
                "titulo": "Lista de sessões",
                "descricao": (
                    "Pesquisar sessões por data, piso, "
                    "profissional, local ou intervenção."
                ),
                "icone": "list",
                "url": "fisioterapia:lista_sessoes",
            },
            {
                "titulo": "Registos por utente",
                "descricao": (
                    "Abrir a ficha do utente e consultar "
                    "o histórico de Fisioterapia."
                ),
                "icone": "users",
                "url": "visitas:lista_utentes",
            },
        ],
    },

    "UCCI_Animacao": {
        "slug": "animacao",
        "titulo": "Animação Sociocultural",
        "descricao": (
            "Atividades e acompanhamento sociocultural."
        ),
        "icone": "smile",
        "cor": "info",
        "acessos": [],
        "mensagem_vazia": (
            "A área está criada. Os módulos de atividades "
            "e planeamento serão adicionados quando essa "
            "parte do projeto for desenvolvida."
        ),
    },

    "UCCI_Cozinha": {
        "slug": "cozinha",
        "titulo": "Cozinha e Alimentação",
        "descricao": "Preparação, entrega e controlo diário de refeições e suplementos.",
        "icone": "coffee",
        "cor": "warning",
        "acessos": [
            {
                "titulo": "Mapa diário",
                "descricao": "Consultar os pedidos de todos os pisos para preparar.",
                "icone": "clipboard",
                "url": "cozinha:mapa_diario",
            },
            {
                "titulo": "Pedidos",
                "descricao": "Acompanhar preparação, entrega e confirmação.",
                "icone": "list",
                "url": "cozinha:lista_pedidos",
            },
            {
                "titulo": "Relatório mensal",
                "descricao": "Totais de refeições e suplementos consumidos.",
                "icone": "bar-chart-2",
                "url": "cozinha:relatorio_mensal",
            },
        ],
    },

    "UCCI_Transportes": {
        "slug": "transportes",
        "titulo": "Transportes",
        "descricao": (
            "Planeamento e execução dos transportes internos."
        ),
        "icone": "truck",
        "cor": "success",
        "acessos": [
            {
                "titulo": "Calendário",
                "descricao": (
                    "Consultar a agenda de transportes."
                ),
                "icone": "calendar",
                "url": "visitas:calendario_transportes",
            },
            {
                "titulo": "Lista de transportes",
                "descricao": (
                    "Pesquisar e acompanhar as deslocações."
                ),
                "icone": "list",
                "url": "visitas:lista_transportes",
            },
            {
                "titulo": "Transportes por confirmar",
                "descricao": (
                    "Confirmar transportes da própria "
                    "instituição."
                ),
                "icone": "check-circle",
                "url": "visitas:lista_transportes",
                "query": (
                    "estado=PENDENTE&meio=INSTITUICAO"
                ),
            },
            {
                "titulo": "Folha diária",
                "descricao": (
                    "Consultar ou imprimir o "
                    "planeamento diário."
                ),
                "icone": "printer",
                "url": (
                    "visitas:relatorio_diario_transportes"
                ),
            },
        ],
    },

    "Financeiro": {
        "slug": "financeiro",
        "titulo": "Financeiro",
        "descricao": (
            "Saldos e movimentos financeiros dos utentes."
        ),
        "icone": "credit-card",
        "cor": "secondary",
        "acessos": [
            {
                "titulo": "Contas dos utentes",
                "descricao": (
                    "Pesquisar utentes e consultar "
                    "os movimentos financeiros."
                ),
                "icone": "credit-card",
                "url": (
                    "visitas:lista_financeira_utentes"
                ),
            },
        ],
    },

    "UCCI_Coordenacao": {
        "slug": "coordenacao",
        "titulo": "Coordenação",
        "descricao": "Supervisão, indicadores e relatórios da UCCI.",
        "icone": "bar-chart-2",
        "cor": "primary",
        "acessos": [
            {
                "titulo": "Visão geral",
                "descricao": "Indicadores consolidados de todas as áreas.",
                "icone": "pie-chart",
                "url": "coordenacao:dashboard_geral",
            },
            {
                "titulo": "Utentes",
                "descricao": "Ocupação, entradas, altas e planeamento.",
                "icone": "users",
                "url": "coordenacao:dashboard_utentes",
            },
            {
                "titulo": "Visitas",
                "descricao": "Fluxo de visitantes e entradas externas.",
                "icone": "user-check",
                "url": "coordenacao:dashboard_visitas",
            },
            {
                "titulo": "Transportes",
                "descricao": "Pedidos, estados, meios e próximas deslocações.",
                "icone": "truck",
                "url": "coordenacao:dashboard_transportes",
            },
            {
                "titulo": "Enfermagem",
                "descricao": "Registos, quedas, notificações e isolamentos.",
                "icone": "heart",
                "url": "coordenacao:dashboard_enfermagem",
            },
            {
                "titulo": "Fisioterapia",
                "descricao": "Sessões, assiduidade e carga por profissional.",
                "icone": "activity",
                "url": "coordenacao:dashboard_fisioterapia",
            },
            {
                "titulo": "Cozinha",
                "descricao": "Pedidos, produção, entregas e consumo.",
                "icone": "coffee",
                "url": "coordenacao:dashboard_cozinha",
            },
            {
                "titulo": "Financeiro",
                "descricao": "Movimentos e saldos das contas dos utentes.",
                "icone": "credit-card",
                "url": "coordenacao:dashboard_financeiro",
            },
        ],
    },


}