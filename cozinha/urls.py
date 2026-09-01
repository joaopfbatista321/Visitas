from django.urls import path

from . import views


app_name = "cozinha"


urlpatterns = [
    path("", views.lista_pedidos, name="lista_pedidos"),
    path("novo/", views.criar_pedido_view, name="criar_pedido"),
    path("mapa-diario/", views.mapa_diario, name="mapa_diario"),
    path("relatorio-mensal/", views.relatorio_mensal, name="relatorio_mensal"),
    path("<int:pk>/", views.detalhe_pedido, name="detalhe_pedido"),
    path("<int:pk>/editar/", views.editar_pedido, name="editar_pedido"),
    path("<int:pk>/enviar/", views.enviar_pedido_view, name="enviar_pedido"),
    path(
        "<int:pk>/iniciar-preparacao/",
        views.iniciar_preparacao_view,
        name="iniciar_preparacao",
    ),
    path("<int:pk>/preparar/", views.preparar_pedido, name="preparar_pedido"),
    path("<int:pk>/entregar/", views.entregar_pedido, name="entregar_pedido"),
    path("<int:pk>/confirmar/", views.confirmar_pedido, name="confirmar_pedido"),
    path("<int:pk>/consumo/", views.consumo_pedido, name="consumo_pedido"),
    path("<int:pk>/reabrir/", views.reabrir_pedido_view, name="reabrir_pedido"),
    path(
    "novo/refeicoes/",
    views.criar_pedido_refeicoes,
    name="criar_pedido_refeicoes",
),
path(
    "novo/suplementos/",
    views.criar_pedido_suplementos,
    name="criar_pedido_suplementos",
),
]
