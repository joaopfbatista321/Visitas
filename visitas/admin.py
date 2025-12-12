from django.contrib import admin
from .models import Quarto, Utente, Visita, Externo


@admin.register(Quarto)
class QuartoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "piso", "descricao")
    list_filter = ("piso",)
    search_fields = ("codigo", "descricao")


@admin.register(Utente)
class UtenteAdmin(admin.ModelAdmin):
    list_display = (
        "nome",
        "numero_processo",
        "quarto",
        "data_entrada",
        "data_saida",
        "ativo",
    )
    list_filter = ("quarto__piso", "quarto", "data_entrada", "data_saida")
    search_fields = ("nome", "numero_processo")


@admin.register(Visita)
class VisitaAdmin(admin.ModelAdmin):
    list_display = (
        "nome_visitante",
        "utente",
        "data_hora_entrada",
        "data_hora_saida",
        "motivo",
        "registado_por",
    )
    list_filter = (
        "utente__quarto__piso",
        "utente",
        "data_hora_entrada",
        "data_hora_saida",
    )
    search_fields = (
        "nome_visitante",
        "utente__nome",
        "utente__numero_processo",
        "motivo",
    )


@admin.register(Externo)
class ExternoAdmin(admin.ModelAdmin):
    list_display = (
        "nome",
        "empresa",
        "tipo_externo",
        "data_hora_entrada",
        "data_hora_saida",
        "destino",
        "registado_por",
    )
    list_filter = (
        "tipo_externo",
        "data_hora_entrada",
        "data_hora_saida",
    )
    search_fields = (
        "nome",
        "empresa",
        "destino",
        "motivo",
    )
