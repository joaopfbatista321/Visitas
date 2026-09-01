from django.urls import path

from . import views


app_name = "fisioterapia"


urlpatterns = [
    path(
        "",
        views.calendario_fisioterapia,
        name="calendario",
    ),
    path(
        "eventos/",
        views.eventos_fisioterapia,
        name="eventos",
    ),
    path(
        "sessoes/",
        views.lista_sessoes,
        name="lista_sessoes",
    ),
    path(
        "sessoes/nova/",
        views.criar_sessao,
        name="criar_sessao",
    ),
    path(
        "sessoes/<int:pk>/",
        views.detalhe_sessao,
        name="detalhe_sessao",
    ),
    path(
        "sessoes/<int:pk>/editar/",
        views.editar_sessao,
        name="editar_sessao",
    ),
    path(
        "sessoes/<int:pk>/realizar-todos/",
        views.marcar_todos_realizados,
        name="marcar_todos_realizados",
    ),
    path(
        "sessoes/<int:pk>/cancelar/",
        views.cancelar_sessao,
        name="cancelar_sessao",
    ),
    path(
        "participacoes/<int:pk>/acao/<str:acao>/",
        views.acao_participacao,
        name="acao_participacao",
    ),
    path(
        "utentes/<int:utente_id>/registos/",
        views.registos_utente,
        name="registos_utente",
    ),
    path(
        "utentes/<int:utente_id>/registos/novo/",
        views.criar_registo,
        name="criar_registo",
    ),
    path(
        (
            "utentes/<int:utente_id>/registos/"
            "novo/<int:participacao_id>/"
        ),
        views.criar_registo,
        name="criar_registo_participacao",
    ),
    path(
        "registos/<int:pk>/",
        views.detalhe_registo,
        name="detalhe_registo",
    ),
    path(
        "registos/<int:pk>/editar/",
        views.editar_registo,
        name="editar_registo",
    ),
    path(
    "alertas-clinicos/",
    views.alertas_clinicos,
    name="alertas_clinicos",
    ),
]