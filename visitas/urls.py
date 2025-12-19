from django.urls import path
from . import views

app_name = "visitas"

urlpatterns = [
    # DASHBOARD PRINCIPAL
    path("", views.dashboard_visitas, name="dashboard_visitas"),

    # UTENTES
    path("utentes/", views.lista_utentes, name="lista_utentes"),
    path("utentes/novo/", views.criar_utente, name="criar_utente"),
    path("utentes/<int:pk>/", views.detalhe_utente, name="detalhe_utente"),
    path("utentes/<int:pk>/editar/", views.editar_utente, name="editar_utente"),
    path("utentes/<int:pk>/saida/", views.saida_utente, name="saida_utente"),


    # VISITAS (relacionadas com utente)
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

    path("visitas/registar/", views.escolher_utente_para_visita, name="escolher_utente_para_visita"),

    path("relatorio/", views.visitas_relatorio, name="visitas_relatorio"),

    path("relatorio/pdf/", views.visitas_relatorio_pdf, name="visitas_relatorio_pdf"),

    # EXTERNOS (prestadores de serviço, técnicos, etc.)
    path("externos/", views.lista_externos, name="lista_externos"),
    path("externos/novo/", views.registar_entrada_externo, name="registar_entrada_externo"),
    path("externos/<int:pk>/saida/", views.registar_saida_externo, name="registar_saida_externo"),

    # RELATÓRIOS / LISTAGENS
    path("hoje/", views.visitas_hoje, name="visitas_hoje"),
    path("ativas/", views.visitas_ativas, name="visitas_ativas"),
    path("relatorio/", views.visitas_relatorio, name="visitas_relatorio"),

    path("isolamentos/ativos/", views.isolamentos_ativos, name="isolamentos_ativos"),
    path("utentes/<int:utente_id>/isolamento/novo/", views.criar_isolamento, name="criar_isolamento"),
    path("isolamentos/<int:isolamento_id>/terminar/", views.terminar_isolamento, name="terminar_isolamento"),

    path("isolamentos/<int:isolamento_id>/editar/", views.editar_isolamento, name="editar_isolamento"),

    path("utente/<int:pk>/financeiro/", views.financeiro_utente, name="financeiro_utente"),


]
