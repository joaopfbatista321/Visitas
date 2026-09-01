from django.urls import path

from . import views


app_name = "coordenacao"


urlpatterns = [
    path("", views.dashboard_geral, name="dashboard_geral"),
    path("utentes/", views.dashboard_utentes, name="dashboard_utentes"),
    path("visitas/", views.dashboard_visitas, name="dashboard_visitas"),
    path(
        "visitas/relatorio.pdf",
        views.relatorio_visitas_pdf,
        name="relatorio_visitas_pdf",
    ),
    path("transportes/", views.dashboard_transportes, name="dashboard_transportes"),
    path("enfermagem/", views.dashboard_enfermagem, name="dashboard_enfermagem"),
    path("fisioterapia/", views.dashboard_fisioterapia, name="dashboard_fisioterapia"),
    path("cozinha/", views.dashboard_cozinha, name="dashboard_cozinha"),
    path("financeiro/", views.dashboard_financeiro, name="dashboard_financeiro"),
]
