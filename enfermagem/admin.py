from django.contrib import admin

from .models import TipoRegistoEnfermagem


@admin.register(TipoRegistoEnfermagem)
class TipoRegistoEnfermagemAdmin(
    admin.ModelAdmin
):
    list_display = [
        "nome",
        "codigo",
        "ativo",
        "ordem",
        "total_registos",
    ]

    list_filter = [
        "ativo",
    ]

    search_fields = [
        "nome",
        "codigo",
        "descricao",
    ]

    list_editable = [
        "ativo",
        "ordem",
    ]

    ordering = [
        "ordem",
        "nome",
    ]

    fieldsets = [
        (
            "Identificação",
            {
                "fields": [
                    "nome",
                    "codigo",
                    "descricao",
                ]
            },
        ),
        (
            "Disponibilidade",
            {
                "fields": [
                    "ativo",
                    "ordem",
                ]
            },
        ),
    ]

    def get_readonly_fields(
        self,
        request,
        obj=None,
    ):
        if obj:
            return ["codigo"]

        return []

    def has_delete_permission(
        self,
        request,
        obj=None,
    ):
        # Os tipos deixam de ser usados através do
        # campo "ativo", mantendo os registos históricos.
        return False

    @admin.display(
        description="Registos",
    )
    def total_registos(self, obj):
        return obj.registos.count()