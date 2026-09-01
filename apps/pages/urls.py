from django.urls import include, path

from . import views


urlpatterns = [
    path(
        "",
        views.index,
        name="index",
    ),

    path(
        "perfil/<slug:slug>/",
        views.perfil_inicio,
        name="perfil_inicio",
    ),

    path(
        "acessos-rapidos/",
        views.acessos_rapidos,
        name="acessos_rapidos",
    ),

    path(
        "dashboard-geral/",
        views.dashboard_coordenacao,
        name="dashboard_geral",
    ),

    path(
        "enfermagem/",
        include("enfermagem.urls"),
    ),

    path(
        "cozinha/",
        include("cozinha.urls"),
    ),

    path("", include("apps.pages.password_urls")),

]