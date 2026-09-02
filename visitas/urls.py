from django.urls import path

from . import views


app_name = "visitas"


urlpatterns = [
    # ========================================================
    # DASHBOARD PRINCIPAL
    # ========================================================
    path("", views.dashboard_visitas, name="dashboard_visitas"),


    
    # ========================================================
    # PEDIDOS DE TRANSPORTE
    # ========================================================
    path(
        "transportes/pedidos/",
        views.lista_pedidos_transporte,
        name="lista_pedidos_transporte",
    ),
    path(
        "transportes/pedidos/novo/",
        views.criar_pedido_transporte,
        name="criar_pedido_transporte",
    ),
    path(
    "transportes/pedidos/<int:pk>/",
    views.detalhe_pedido_transporte,
    name="detalhe_pedido_transporte",
    ),

    path(
    "transportes/pedidos/<int:pk>/validar/",
    views.validar_pedido_transporte,
    name="validar_pedido_transporte",
    ),

    # ========================================================
    # TRANSPORTES DE UTENTES
    # ========================================================
    
    path(
        "transportes/",
        views.calendario_transportes,
        name="calendario_transportes",
    ),
    path(
        "transportes/eventos/",
        views.eventos_transportes,
        name="eventos_transportes",
    ),
    path(
        "transportes/lista/",
        views.lista_transportes,
        name="lista_transportes",
    ),
    path(
        "transportes/novo/",
        views.criar_transporte,
        name="criar_transporte",
    ),
    path(
        "transportes/relatorio/diario/",
        views.relatorio_diario_transportes,
        name="relatorio_diario_transportes",
    ),

    # VIATURAS
    path(
        "transportes/viaturas/",
        views.lista_viaturas,
        name="lista_viaturas",
    ),
    path(
        "transportes/viaturas/nova/",
        views.gerir_viatura,
        name="criar_viatura",
    ),
    path(
        "transportes/viaturas/<int:pk>/editar/",
        views.gerir_viatura,
        name="editar_viatura",
    ),

    # CONDUTORES
    path(
        "transportes/condutores/",
        views.lista_condutores,
        name="lista_condutores",
    ),
    path(
        "transportes/condutores/novo/",
        views.gerir_condutor,
        name="criar_condutor",
    ),
    path(
        "transportes/condutores/<int:pk>/editar/",
        views.gerir_condutor,
        name="editar_condutor",
    ),

    # INDISPONIBILIDADES DE VIATURAS E CONDUTORES
    path(
        "transportes/indisponibilidades/",
        views.lista_indisponibilidades,
        name="lista_indisponibilidades",
    ),
    path(
        "transportes/indisponibilidades/nova/",
        views.gerir_indisponibilidade,
        name="criar_indisponibilidade",
    ),
    path(
        "transportes/indisponibilidades/<int:pk>/editar/",
        views.gerir_indisponibilidade,
        name="editar_indisponibilidade",
    ),
    path(
        "transportes/indisponibilidades/<int:pk>/apagar/",
        views.apagar_indisponibilidade,
        name="apagar_indisponibilidade",
    ),

    # DETALHE, EDIÇÃO E AÇÕES DO TRANSPORTE
    # Estas rotas ficam depois das rotas fixas para evitar conflitos.
    path(
        "transportes/<int:pk>/",
        views.detalhe_transporte,
        name="detalhe_transporte",
    ),
    path(
        "transportes/<int:pk>/editar/",
        views.editar_transporte,
        name="editar_transporte",
    ),
    path(
        "transportes/<int:pk>/acao/<str:acao>/",
        views.acao_transporte,
        name="acao_transporte",
    ),

    # ========================================================
    # UTENTES
    # ========================================================
    path("utentes/", views.lista_utentes, name="lista_utentes"),
    path("utentes/novo/", views.criar_utente, name="criar_utente"),
    path("utentes/<int:pk>/", views.detalhe_utente, name="detalhe_utente"),
    path("utentes/<int:pk>/editar/", views.editar_utente, name="editar_utente"),
    path("utentes/<int:pk>/saida/", views.saida_utente, name="saida_utente"),

    # ========================================================
    # VISITAS RELACIONADAS COM UTENTES
    # ========================================================
    path(
        "utentes/<int:utente_id>/visitas/nova/",
        views.registar_visita_utente,
        name="registar_visita_utente",
    ),
    path(
        "visitas/<int:visita_id>/saida/",
        views.registar_saida_visita,
        name="registar_saida_visita",
    ),
    path(
        "visitas/registar/",
        views.escolher_utente_para_visita,
        name="escolher_utente_para_visita",
    ),

    # ========================================================
    # EXTERNOS
    # ========================================================
    path("externos/", views.lista_externos, name="lista_externos"),
    path(
        "externos/novo/",
        views.registar_entrada_externo,
        name="registar_entrada_externo",
    ),
    path(
        "externos/<int:pk>/saida/",
        views.registar_saida_externo,
        name="registar_saida_externo",
    ),

    # ========================================================
    # RELATÓRIOS E LISTAGENS DE VISITAS
    # ========================================================
    path("hoje/", views.visitas_hoje, name="visitas_hoje"),
    path("ativas/", views.visitas_ativas, name="visitas_ativas"),
    path("relatorio/", views.visitas_relatorio, name="visitas_relatorio"),
    path(
        "relatorio/pdf/",
        views.visitas_relatorio_pdf,
        name="visitas_relatorio_pdf",
    ),

    # ========================================================
    # ISOLAMENTOS
    # ========================================================
    path(
        "isolamentos/ativos/",
        views.isolamentos_ativos,
        name="isolamentos_ativos",
    ),
    path(
        "utentes/<int:utente_id>/isolamento/novo/",
        views.criar_isolamento,
        name="criar_isolamento",
    ),
    path(
        "isolamentos/<int:isolamento_id>/terminar/",
        views.terminar_isolamento,
        name="terminar_isolamento",
    ),
    path(
        "isolamentos/<int:isolamento_id>/editar/",
        views.editar_isolamento,
        name="editar_isolamento",
    ),

    # ========================================================
    # FINANCEIRO
    # ========================================================
    path(
        "financeiro/",
        views.lista_financeira_utentes,
        name="lista_financeira_utentes",
    ),
    path(
        "financeiro/mensalidades/",
        views.mensalidades_utentes,
        name="mensalidades_utentes",
    ),
    path(
        "financeiro/mensalidades/utente/<int:pk>/configurar/",
        views.configuracao_mensalidade_utente,
        name="configuracao_mensalidade_utente",
    ),
    path(
        "financeiro/mensalidades/<int:pk>/validar/",
        views.validar_pagamento_mensalidade,
        name="validar_pagamento_mensalidade",
    ),
    path(
        "utente/<int:pk>/financeiro/",
        views.financeiro_utente,
        name="financeiro_utente",
    ),
    path(
        "mapa-ocupacao/",
        views.mapa_ocupacao,
        name="mapa_ocupacao",
    ),
]
