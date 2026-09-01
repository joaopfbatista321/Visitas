from django.contrib import admin

from .models import (
    HistoricoPedidoCozinha,
    LinhaProdutoPedido,
    LinhaRefeicaoPedido,
    PedidoCozinha,
    ProdutoCozinha,
    TipoDieta,
    TipoRefeicao,
    UnidadeCozinha,
)


@admin.register(UnidadeCozinha)
class UnidadeCozinhaAdmin(admin.ModelAdmin):
    list_display = (
        "codigo",
        "nome",
        "ativa",
        "ordem",
        "total_enfermeiros",
    )
    list_display_links = (
        "codigo",
        "nome",
    )
    list_editable = (
        "ativa",
        "ordem",
    )
    list_filter = ("ativa",)
    search_fields = (
        "codigo",
        "nome",
        "enfermeiros__username",
        "enfermeiros__first_name",
        "enfermeiros__last_name",
    )
    filter_horizontal = ("enfermeiros",)
    ordering = (
        "ordem",
        "nome",
    )

    @admin.display(description="Enfermeiros")
    def total_enfermeiros(self, obj):
        return obj.enfermeiros.count()

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related("enfermeiros")
        )

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ProdutoCozinha)
class ProdutoCozinhaAdmin(admin.ModelAdmin):
    list_display = (
        "codigo",
        "nome",
        "categoria",
        "unidade_medida",
        "ativo",
        "ordem",
    )
    list_display_links = (
        "codigo",
        "nome",
    )
    list_editable = (
        "ativo",
        "ordem",
    )
    list_filter = (
        "ativo",
        "categoria",
        "unidade_medida",
    )
    search_fields = (
        "codigo",
        "nome",
        "descricao",
    )
    ordering = (
        "ordem",
        "nome",
    )

    def has_delete_permission(self, request, obj=None):
        return False


class BaseTipoAdmin(admin.ModelAdmin):
    list_display = (
        "codigo",
        "nome",
        "ativo",
        "ordem",
    )
    list_display_links = (
        "codigo",
        "nome",
    )
    list_editable = (
        "ativo",
        "ordem",
    )
    list_filter = ("ativo",)
    search_fields = (
        "codigo",
        "nome",
        "descricao",
    )
    ordering = (
        "ordem",
        "nome",
    )

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(TipoRefeicao)
class TipoRefeicaoAdmin(BaseTipoAdmin):
    pass


@admin.register(TipoDieta)
class TipoDietaAdmin(BaseTipoAdmin):
    pass


class LinhaProdutoPedidoInline(admin.TabularInline):
    model = LinhaProdutoPedido
    extra = 0
    can_delete = False
    fields = (
        "produto",
        "quantidade_solicitada",
        "quantidade_preparada",
        "quantidade_entregue",
        "quantidade_recebida",
        "quantidade_consumida",
    )
    readonly_fields = fields
    show_change_link = False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class LinhaRefeicaoPedidoInline(admin.TabularInline):
    model = LinhaRefeicaoPedido
    extra = 0
    can_delete = False
    fields = (
        "tipo_refeicao",
        "tipo_dieta",
        "quantidade_solicitada",
        "quantidade_preparada",
        "quantidade_entregue",
        "quantidade_recebida",
        "quantidade_consumida",
    )
    readonly_fields = fields
    show_change_link = False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class HistoricoPedidoCozinhaInline(admin.TabularInline):
    model = HistoricoPedidoCozinha
    extra = 0
    can_delete = False
    fields = (
        "criado_em",
        "acao",
        "estado_anterior",
        "estado_novo",
        "profissional",
        "observacao",
    )
    readonly_fields = fields
    ordering = ("-criado_em", "-pk")
    show_change_link = False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PedidoCozinha)
class PedidoCozinhaAdmin(admin.ModelAdmin):
    list_display = (
        "data_servico",
        "unidade",
        "estado",
        "criado_por",
        "enviado_em",
        "preparacao_em",
        "entregue_em",
        "confirmado_em",
    )
    list_filter = (
        "estado",
        "unidade",
        "data_servico",
    )
    search_fields = (
        "unidade__codigo",
        "unidade__nome",
        "criado_por__username",
        "criado_por__first_name",
        "criado_por__last_name",
        "observacoes_enfermagem",
        "observacoes_cozinha",
        "observacoes_confirmacao",
    )
    date_hierarchy = "data_servico"
    ordering = (
        "-data_servico",
        "unidade__ordem",
        "unidade__nome",
    )
    list_select_related = (
        "unidade",
        "criado_por",
        "enviado_por",
        "preparacao_por",
        "entregue_por",
        "confirmado_por",
        "reaberto_por",
    )
    readonly_fields = (
        "unidade",
        "data_servico",
        "estado",
        "observacoes_enfermagem",
        "observacoes_cozinha",
        "observacoes_confirmacao",
        "criado_por",
        "enviado_por",
        "enviado_em",
        "preparacao_por",
        "preparacao_em",
        "entregue_por",
        "entregue_em",
        "confirmado_por",
        "confirmado_em",
        "reaberto_por",
        "reaberto_em",
        "motivo_reabertura",
        "criado_em",
        "atualizado_em",
        "prazo_edicao_admin",
    )
    fieldsets = (
        (
            "Pedido",
            {
                "fields": (
                    "unidade",
                    "data_servico",
                    "estado",
                    "prazo_edicao_admin",
                )
            },
        ),
        (
            "Observações",
            {
                "fields": (
                    "observacoes_enfermagem",
                    "observacoes_cozinha",
                    "observacoes_confirmacao",
                )
            },
        ),
        (
            "Responsáveis e datas",
            {
                "fields": (
                    "criado_por",
                    "criado_em",
                    "enviado_por",
                    "enviado_em",
                    "preparacao_por",
                    "preparacao_em",
                    "entregue_por",
                    "entregue_em",
                    "confirmado_por",
                    "confirmado_em",
                    "atualizado_em",
                )
            },
        ),
        (
            "Reabertura",
            {
                "fields": (
                    "reaberto_por",
                    "reaberto_em",
                    "motivo_reabertura",
                ),
                "classes": ("collapse",),
            },
        ),
    )
    inlines = (
        LinhaProdutoPedidoInline,
        LinhaRefeicaoPedidoInline,
        HistoricoPedidoCozinhaInline,
    )

    @admin.display(description="Prazo de edição")
    def prazo_edicao_admin(self, obj):
        if not obj or not obj.data_servico:
            return "—"

        return obj.prazo_edicao

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(HistoricoPedidoCozinha)
class HistoricoPedidoCozinhaAdmin(admin.ModelAdmin):
    list_display = (
        "criado_em",
        "pedido",
        "acao",
        "estado_anterior",
        "estado_novo",
        "profissional",
    )
    list_filter = (
        "acao",
        "estado_novo",
        "criado_em",
    )
    search_fields = (
        "pedido__unidade__nome",
        "pedido__unidade__codigo",
        "profissional__username",
        "profissional__first_name",
        "profissional__last_name",
        "observacao",
    )
    date_hierarchy = "criado_em"
    ordering = ("-criado_em", "-pk")
    list_select_related = (
        "pedido",
        "pedido__unidade",
        "profissional",
    )
    readonly_fields = (
        "pedido",
        "acao",
        "estado_anterior",
        "estado_novo",
        "dados",
        "observacao",
        "profissional",
        "criado_em",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
