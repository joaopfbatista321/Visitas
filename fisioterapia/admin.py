from django.contrib import admin

from .models import TipoIntervencaoFisioterapia


@admin.register(TipoIntervencaoFisioterapia)
class TipoIntervencaoFisioterapiaAdmin(
    admin.ModelAdmin
):
    list_display = [
        "nome",
        "categoria",
        "ativo",
        "ordem",
    ]

    list_filter = [
        "categoria",
        "ativo",
    ]

    search_fields = [
        "nome",
        "descricao",
    ]

    list_editable = [
        "ativo",
        "ordem",
    ]

    ordering = [
        "ordem",
        "categoria",
        "nome",
    ]

    fieldsets = [
        (
            "Identificação",
            {
                "fields": [
                    "nome",
                    "categoria",
                    "descricao",
                ],
            },
        ),
        (
            "Disponibilidade",
            {
                "fields": [
                    "ativo",
                    "ordem",
                ],
            },
        ),
    ]