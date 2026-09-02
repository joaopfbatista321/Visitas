from django.contrib import admin
from .models import (
    Externo,
    Isolamento,
    Mensalidade,
    MovimentoFinanceiro,
    PagamentoMensalidade,
    Quarto,
    Utente,
    Visita,
)


# =========================
# QUARTO
# =========================
@admin.register(Quarto)
class QuartoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "piso", "capacidade", "descricao")
    list_filter = ("piso",)
    search_fields = ("codigo", "descricao")


# =========================
# ISOLAMENTO INLINE (TEM DE VIR ANTES)
# =========================
class IsolamentoInline(admin.TabularInline):
    model = Isolamento
    extra = 0
    readonly_fields = ("data_inicio", "data_fim", "ativo")
    can_delete = False
    ordering = ("-data_inicio",)
    
class MovimentoFinanceiroInline(admin.TabularInline):
    model = MovimentoFinanceiro
    extra = 0
    readonly_fields = ("data", "registado_por")

# =========================
# UTENTE
# =========================
@admin.register(Utente)
class UtenteAdmin(admin.ModelAdmin):
    list_display = (
        "nome",
        "numero_processo",
        "quarto",
        "valor_caucao",
        "valor_dia",
        "paga_dias_ausencia",
        "ativo",
        "em_isolamento",
    )

    list_filter = (
        "data_saida",
        "quarto",
    )

    search_fields = (
        "nome",
        "numero_processo",
    )


    inlines = [IsolamentoInline, MovimentoFinanceiroInline]


    def em_isolamento(self, obj):
        return obj.isolamento_ativo is not None

    em_isolamento.boolean = True
    em_isolamento.short_description = "Em isolamento"


# =========================
# VISITA
# =========================
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


# =========================
# EXTERNO
# =========================
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


# =========================
# ISOLAMENTO (ADMIN PRINCIPAL)
# =========================
@admin.register(Isolamento)
class IsolamentoAdmin(admin.ModelAdmin):
    list_display = (
        "utente",
        "tipo",
        "data_inicio",
        "data_fim",
        "ativo",
    )

    list_filter = (
        "tipo",
        "ativo",
        "data_inicio",
    )

    search_fields = (
        "utente__nome",
        "utente__numero_processo",
        "motivo",
    )

    ordering = ("-data_inicio",)

    autocomplete_fields = ("utente",)

    readonly_fields = ("data_inicio",)

    fieldsets = (
        ("Utente", {
            "fields": ("utente",)
        }),
        ("Tipo de isolamento", {
            "fields": ("tipo",),
            "description": "Tipo de isolamento clínico aplicado ao utente."
        }),
        ("Período", {
            "fields": ("data_inicio", "data_fim")
        }),
        ("Informação clínica", {
            "fields": ("motivo", "observacoes")
        }),
        ("Estado", {
            "fields": ("ativo",)
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        """
        Bloqueia edição do isolamento depois de terminado
        """
        if obj and not obj.ativo:
            return self.readonly_fields + (
                "utente",
                "tipo",
                "motivo",
                "observacoes",
                "data_fim",
            )
        return self.readonly_fields


@admin.register(MovimentoFinanceiro)
class MovimentoFinanceiroAdmin(admin.ModelAdmin):
    list_display = (
        "utente",
        "tipo",
        "valor",
        "descricao",
        "data",
        "registado_por",
    )

    list_filter = ("tipo", "data")
    search_fields = ("utente__nome", "descricao")


@admin.register(Mensalidade)
class MensalidadeAdmin(admin.ModelAdmin):
    list_display = (
        "utente",
        "ano",
        "mes",
        "dias_faturaveis",
        "valor_total",
        "pago",
        "necessita_revisao",
        "confirmado_por",
    )
    list_filter = ("ano", "mes", "pago", "necessita_revisao")
    search_fields = ("utente__nome", "utente__numero_processo")
    readonly_fields = (
        "utente",
        "ano",
        "mes",
        "valor_dia",
        "dias_estadia",
        "dias_ausencia",
        "dias_faturaveis",
        "valor_total",
        "pago",
        "pago_em",
        "observacoes",
        "confirmado_por",
        "necessita_revisao",
        "criado_em",
        "atualizado_em",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PagamentoMensalidade)
class PagamentoMensalidadeAdmin(admin.ModelAdmin):
    list_display = (
        "mensalidade",
        "valor",
        "data_pagamento",
        "registado_por",
        "criado_em",
    )
    list_filter = ("data_pagamento", "criado_em")
    search_fields = (
        "mensalidade__utente__nome",
        "mensalidade__utente__numero_processo",
        "observacoes",
    )
    readonly_fields = (
        "mensalidade",
        "valor",
        "data_pagamento",
        "observacoes",
        "registado_por",
        "criado_em",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
