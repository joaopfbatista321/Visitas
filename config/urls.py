"""Configuração principal das rotas do projeto."""

from django.contrib import admin
from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token


urlpatterns = [
    # Páginas principais
    path(
        "",
        include("apps.pages.urls"),
    ),

    # Componentes do Datta Able
    path(
        "",
        include("apps.dyn_dt.urls"),
    ),
    path(
        "",
        include("apps.dyn_api.urls"),
    ),
    path(
        "charts/",
        include("apps.charts.urls"),
    ),
    path(
        "",
        include("admin_datta.urls"),
    ),

    # Administração
    path(
        "admin/",
        admin.site.urls,
    ),

    # Aplicações
    path(
        "visitas/",
        include("visitas.urls"),
    ),
    path(
        "fisioterapia/",
        include("fisioterapia.urls"),
    ),
    path(
        "coordenacao/",
        include("coordenacao.urls"),
    ),
]


# API opcional
try:
    urlpatterns += [
        path(
            "api/",
            include("api.urls"),
        ),
        path(
            "login/jwt/",
            obtain_auth_token,
            name="login_jwt",
        ),
    ]
except (ImportError, ModuleNotFoundError):
    pass