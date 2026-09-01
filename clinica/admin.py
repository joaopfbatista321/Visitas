from django import forms
from django.contrib import admin

from .models import AreaClinica


class AreaClinicaAdminForm(forms.ModelForm):
    class Meta:
        model = AreaClinica
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()

        ativa = cleaned_data.get("ativa")
        grupos_responsaveis = cleaned_data.get(
            "grupos_responsaveis"
        )
        grupos_partilha_geral = cleaned_data.get(
            "grupos_partilha_geral"
        )

        if (
            ativa
            and grupos_responsaveis is not None
            and not grupos_responsaveis.exists()
        ):
            self.add_error(
                "grupos_responsaveis",
                (
                    "Uma área clínica ativa deve ter pelo "
                    "menos uma equipa responsável."
                ),
            )

        if (
            grupos_responsaveis is not None
            and grupos_partilha_geral is not None
        ):
            ids_partilha = grupos_partilha_geral.values_list(
                "pk",
                flat=True,
            )

            grupos_em_falta = grupos_responsaveis.exclude(
                pk__in=ids_partilha,
            )

            if grupos_em_falta.exists():
                nomes = ", ".join(
                    grupos_em_falta.values_list(
                        "name",
                        flat=True,
                    )
                )

                self.add_error(
                    "grupos_partilha_geral",
                    (
                        "As equipas responsáveis também "
                        "devem estar incluídas no acesso geral: "
                        f"{nomes}."
                    ),
                )

        return cleaned_data


@admin.register(AreaClinica)
class AreaClinicaAdmin(admin.ModelAdmin):
    form = AreaClinicaAdminForm

    list_display = [
        "nome",
        "codigo",
        "ativa",
        "total_grupos_responsaveis",
        "total_grupos_partilha",
        "atualizado_em",
    ]

    list_filter = [
        "ativa",
    ]

    search_fields = [
        "nome",
        "codigo",
        "descricao",
        "grupos_responsaveis__name",
        "grupos_partilha_geral__name",
    ]

    filter_horizontal = [
        "grupos_responsaveis",
        "grupos_partilha_geral",
    ]

    readonly_fields = [
        "criado_em",
        "atualizado_em",
    ]

    fieldsets = [
        (
            "Identificação",
            {
                "fields": [
                    "nome",
                    "codigo",
                    "descricao",
                    "ativa",
                ]
            },
        ),
        (
            "Permissões da área",
            {
                "fields": [
                    "grupos_responsaveis",
                    "grupos_partilha_geral",
                ],
                "description": (
                    "Defina quais as equipas responsáveis "
                    "pela área e quais podem consultar os "
                    "registos clínicos partilhados."
                ),
            },
        ),
        (
            "Informação do sistema",
            {
                "fields": [
                    "criado_em",
                    "atualizado_em",
                ],
                "classes": ["collapse"],
            },
        ),
    ]

    def get_readonly_fields(self, request, obj=None):
        campos = list(self.readonly_fields)

        if obj:
            campos.append("codigo")

        return campos

    def has_delete_permission(
        self,
        request,
        obj=None,
    ):
        # As configurações são desativadas, não apagadas,
        # para não quebrar os acessos aos registos clínicos.
        return False

    @admin.display(
        description="Equipas responsáveis",
    )
    def total_grupos_responsaveis(self, obj):
        return obj.grupos_responsaveis.count()

    @admin.display(
        description="Equipas com acesso",
    )
    def total_grupos_partilha(self, obj):
        return obj.grupos_partilha_geral.count()