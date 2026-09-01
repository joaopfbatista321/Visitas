from django.urls import path

from . import views
from .calendario_reabilitacao import (
    calendario_reabilitacao_enfermagem,
    eventos_reabilitacao_enfermagem,
)


app_name = "enfermagem"


urlpatterns = [
    path(
        "utentes/<int:utente_pk>/",
        views.registos_utente,
        name="registos_utente",
    ),
    path(
        "utentes/<int:utente_pk>/novo/",
        views.criar_registo,
        name="criar_registo",
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
        "quedas/",
        views.lista_quedas,
        name="lista_quedas",
    ),
    path(
        "utentes/<int:utente_pk>/quedas/nova/",
        views.criar_queda,
        name="criar_queda",
    ),
    path(
        "quedas/<int:pk>/",
        views.detalhe_queda,
        name="detalhe_queda",
    ),
    path(
        "quedas/<int:pk>/editar/",
        views.editar_queda,
        name="editar_queda",
    ),
    path(
        "ausencias/",
        views.lista_ausencias,
        name="lista_ausencias",
    ),
    path(
        "utentes/<int:utente_pk>/ausencias/nova/",
        views.criar_ausencia,
        name="criar_ausencia",
    ),
    path(
        "ausencias/<int:pk>/",
        views.detalhe_ausencia,
        name="detalhe_ausencia",
    ),
    path(
        "ausencias/<int:pk>/editar/",
        views.editar_ausencia,
        name="editar_ausencia",
    ),
    path(
        "ausencias/<int:pk>/regresso/",
        views.registar_regresso_ausencia,
        name="registar_regresso_ausencia",
    ),
    path(
        "ausencias/<int:pk>/cancelar/",
        views.cancelar_ausencia,
        name="cancelar_ausencia",
    ),
    path(
        "calendario-reabilitacao/",
        calendario_reabilitacao_enfermagem,
        name="calendario_reabilitacao",
    ),
    path(
        "calendario-reabilitacao/eventos/",
        eventos_reabilitacao_enfermagem,
        name="eventos_reabilitacao",
    ),
]
