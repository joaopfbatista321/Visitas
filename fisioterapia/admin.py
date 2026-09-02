from django.contrib import admin

from .models import TipoIntervencaoFisioterapia


@admin.register(TipoIntervencaoFisioterapia)
class TipoIntervencaoFisioterapiaAdmin(
    admin.ModelAdmin
):
    list_display = [
        "nome",
        "area",
        "categoria",
        "ativo",
        "ordem",
    ]

    list_filter = [
        "area",
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
        "area",
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
                    "area",
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
