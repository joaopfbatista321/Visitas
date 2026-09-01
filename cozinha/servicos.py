from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)
from django.db import transaction
from django.utils import timezone

from .models import (
    AcaoHistoricoCozinha,
    EstadoPedidoCozinha,
    HistoricoPedidoCozinha,
    LinhaProdutoPedido,
    LinhaRefeicaoPedido,
    PedidoCozinha,
    ProdutoCozinha,
    TipoDieta,
    TipoPedidoCozinha,
    TipoRefeicao,
)
from .permissoes import (
    pode_confirmar_rececao,
    pode_editar_quantidades,
    pode_enviar_pedido,
    pode_iniciar_preparacao,
    pode_registar_consumo,
    pode_registar_entrega,
    pode_reabrir_pedido,
)


def registar_historico(
    pedido,
    acao,
    profissional,
    estado_anterior="",
    observacao="",
):
    pedido._prefetched_objects_cache = {}

    return HistoricoPedidoCozinha.objects.create(
        pedido=pedido,
        acao=acao,
        estado_anterior=estado_anterior,
        estado_novo=pedido.estado,
        dados=pedido.dados_para_historico(),
        observacao=observacao,
        profissional=profissional,
    )


def garantir_linhas_pedido(pedido):
    """
    Cria apenas as linhas correspondentes ao tipo do pedido.
    """

    if pedido.tipo == TipoPedidoCozinha.SUPLEMENTOS:
        produtos_existentes = set(
            pedido.linhas_produtos.values_list(
                "produto_id",
                flat=True,
            )
        )

        produtos_novos = [
            LinhaProdutoPedido(
                pedido=pedido,
                produto=produto,
            )
            for produto in ProdutoCozinha.objects.filter(
                ativo=True
            )
            if produto.pk not in produtos_existentes
        ]

        if produtos_novos:
            LinhaProdutoPedido.objects.bulk_create(
                produtos_novos,
                ignore_conflicts=True,
            )

        return

    if pedido.tipo != TipoPedidoCozinha.REFEICOES:
        raise ValidationError(
            "O tipo do pedido à Cozinha não é válido."
        )

    refeicoes_existentes = set(
        pedido.linhas_refeicoes.values_list(
            "tipo_refeicao_id",
            "tipo_dieta_id",
        )
    )

    refeicoes = TipoRefeicao.objects.filter(ativo=True)
    dietas = TipoDieta.objects.filter(ativo=True)

    linhas_refeicao_novas = []

    for refeicao in refeicoes:
        for dieta in dietas:
            identificador = (
                refeicao.pk,
                dieta.pk,
            )

            if identificador not in refeicoes_existentes:
                linhas_refeicao_novas.append(
                    LinhaRefeicaoPedido(
                        pedido=pedido,
                        tipo_refeicao=refeicao,
                        tipo_dieta=dieta,
                    )
                )

    if linhas_refeicao_novas:
        LinhaRefeicaoPedido.objects.bulk_create(
            linhas_refeicao_novas,
            ignore_conflicts=True,
        )


def pedido_tem_quantidades(pedido):
    if pedido.tipo == TipoPedidoCozinha.REFEICOES:
        return pedido.linhas_refeicoes.filter(
            quantidade_solicitada__gt=0
        ).exists()

    if pedido.tipo == TipoPedidoCozinha.SUPLEMENTOS:
        return pedido.linhas_produtos.filter(
            quantidade_solicitada__gt=0
        ).exists()

    return False


def _validar_formset(pedido, formset):
    if pedido.tipo == TipoPedidoCozinha.REFEICOES:
        modelo_esperado = LinhaRefeicaoPedido
    elif pedido.tipo == TipoPedidoCozinha.SUPLEMENTOS:
        modelo_esperado = LinhaProdutoPedido
    else:
        raise ValidationError(
            "O tipo do pedido à Cozinha não é válido."
        )

    if getattr(formset, "model", None) is not modelo_esperado:
        raise ValidationError(
            "As linhas enviadas não correspondem ao tipo do pedido."
        )

    if (
        getattr(
            getattr(formset, "instance", None),
            "pk",
            None,
        )
        != pedido.pk
    ):
        raise ValidationError(
            "As linhas enviadas não pertencem a este pedido."
        )

    if not formset.is_valid():
        raise ValidationError(
            "Existem erros nas quantidades indicadas."
        )


def _bloquear_pedido(pedido):
    return (
        PedidoCozinha.objects
        .select_for_update()
        .select_related("unidade")
        .get(pk=pedido.pk)
    )


@transaction.atomic
def criar_pedido(formulario, utilizador):
    pedido = formulario.save(commit=False)
    pedido.criado_por = utilizador
    pedido.estado = EstadoPedidoCozinha.RASCUNHO

    pedido.full_clean()
    pedido.save()

    garantir_linhas_pedido(pedido)

    registar_historico(
        pedido=pedido,
        acao=AcaoHistoricoCozinha.CRIADO,
        profissional=utilizador,
    )

    return pedido


@transaction.atomic
def guardar_quantidades_solicitadas(
    pedido,
    linhas_formset,
    utilizador,
    observacoes_enfermagem=None,
):
    pedido = _bloquear_pedido(pedido)

    if not pode_editar_quantidades(
        utilizador,
        pedido,
    ):
        raise PermissionDenied(
            "Não pode alterar as quantidades deste pedido."
        )

    _validar_formset(pedido, linhas_formset)
    linhas_formset.save()

    if observacoes_enfermagem is not None:
        pedido.observacoes_enfermagem = (
            observacoes_enfermagem
        )
        pedido.save()

    registar_historico(
        pedido=pedido,
        acao=AcaoHistoricoCozinha.ALTERADO,
        profissional=utilizador,
    )

    return pedido


@transaction.atomic
def enviar_pedido(pedido, utilizador):
    pedido = _bloquear_pedido(pedido)

    if not pode_enviar_pedido(
        utilizador,
        pedido,
    ):
        raise PermissionDenied(
            "Não pode enviar este pedido."
        )

    if not pedido_tem_quantidades(pedido):
        raise ValidationError(
            "Indique pelo menos uma quantidade antes de enviar."
        )

    estado_anterior = pedido.estado

    pedido.estado = EstadoPedidoCozinha.ENVIADO
    pedido.enviado_por = utilizador
    pedido.enviado_em = timezone.now()

    pedido.full_clean()
    pedido.save()

    registar_historico(
        pedido=pedido,
        acao=AcaoHistoricoCozinha.ENVIADO,
        profissional=utilizador,
        estado_anterior=estado_anterior,
    )

    return pedido


def _preencher_quantidades_preparadas(pedido):
    if pedido.tipo == TipoPedidoCozinha.REFEICOES:
        linhas = pedido.linhas_refeicoes.select_for_update()
    elif pedido.tipo == TipoPedidoCozinha.SUPLEMENTOS:
        linhas = pedido.linhas_produtos.select_for_update()
    else:
        raise ValidationError(
            "O tipo do pedido à Cozinha não é válido."
        )

    for linha in linhas:
        if linha.quantidade_preparada is None:
            linha.quantidade_preparada = (
                linha.quantidade_solicitada
            )
            linha.save(
                update_fields=["quantidade_preparada"]
            )


@transaction.atomic
def iniciar_preparacao(pedido, utilizador):
    pedido = _bloquear_pedido(pedido)

    if not pode_iniciar_preparacao(
        utilizador,
        pedido,
    ):
        raise PermissionDenied(
            "Este pedido ainda não pode entrar em preparação."
        )

    estado_anterior = pedido.estado

    _preencher_quantidades_preparadas(pedido)

    pedido.estado = EstadoPedidoCozinha.EM_PREPARACAO
    pedido.preparacao_por = utilizador
    pedido.preparacao_em = timezone.now()

    pedido.full_clean()
    pedido.save()

    registar_historico(
        pedido=pedido,
        acao=AcaoHistoricoCozinha.EM_PREPARACAO,
        profissional=utilizador,
        estado_anterior=estado_anterior,
    )

    return pedido


@transaction.atomic
def guardar_preparacao(
    pedido,
    linhas_formset,
    utilizador,
    observacoes_cozinha="",
):
    pedido = _bloquear_pedido(pedido)

    if not pode_registar_entrega(utilizador, pedido):
        raise PermissionDenied(
            "Não pode alterar a preparação deste pedido."
        )

    _validar_formset(pedido, linhas_formset)
    linhas_formset.save()

    pedido.observacoes_cozinha = observacoes_cozinha
    pedido.save()

    registar_historico(
        pedido=pedido,
        acao=AcaoHistoricoCozinha.ALTERADO,
        profissional=utilizador,
        observacao="Quantidades preparadas atualizadas.",
    )

    return pedido


@transaction.atomic
def registar_entrega(
    pedido,
    linhas_formset,
    utilizador,
    observacoes_cozinha="",
):
    pedido = _bloquear_pedido(pedido)

    if not pode_registar_entrega(
        utilizador,
        pedido,
    ):
        raise PermissionDenied(
            "Não pode registar a entrega deste pedido."
        )

    _validar_formset(pedido, linhas_formset)
    linhas_formset.save()

    estado_anterior = pedido.estado

    pedido.estado = EstadoPedidoCozinha.ENTREGUE
    pedido.entregue_por = utilizador
    pedido.entregue_em = timezone.now()
    pedido.observacoes_cozinha = observacoes_cozinha

    pedido.full_clean()
    pedido.save()

    registar_historico(
        pedido=pedido,
        acao=AcaoHistoricoCozinha.ENTREGUE,
        profissional=utilizador,
        estado_anterior=estado_anterior,
    )

    return pedido


@transaction.atomic
def confirmar_rececao(
    pedido,
    produtos_formset,
    utilizador,
    observacoes_confirmacao="",
):
    pedido = _bloquear_pedido(pedido)

    if pedido.tipo != TipoPedidoCozinha.SUPLEMENTOS:
        raise ValidationError(
            "As refeições não necessitam de confirmação pela Enfermagem."
        )

    if not pode_confirmar_rececao(
        utilizador,
        pedido,
    ):
        raise PermissionDenied(
            "Não pode confirmar a receção deste pedido."
        )

    _validar_formset(pedido, produtos_formset)
    produtos_formset.save()

    pedido._prefetched_objects_cache = {}

    estado_anterior = pedido.estado

    if pedido.tem_divergencias:
        pedido.estado = EstadoPedidoCozinha.DIVERGENCIA
        acao = AcaoHistoricoCozinha.DIVERGENCIA
    else:
        pedido.estado = EstadoPedidoCozinha.CONFIRMADO
        acao = AcaoHistoricoCozinha.CONFIRMADO

    pedido.confirmado_por = utilizador
    pedido.confirmado_em = timezone.now()
    pedido.observacoes_confirmacao = (
        observacoes_confirmacao
    )

    pedido.full_clean()
    pedido.save()

    registar_historico(
        pedido=pedido,
        acao=acao,
        profissional=utilizador,
        estado_anterior=estado_anterior,
    )

    return pedido


@transaction.atomic
def registar_consumo(
    pedido,
    produtos_formset,
    utilizador,
    observacoes_confirmacao="",
):
    pedido = _bloquear_pedido(pedido)

    if pedido.tipo != TipoPedidoCozinha.SUPLEMENTOS:
        raise ValidationError(
            "O consumo separado aplica-se apenas aos suplementos."
        )

    if not pode_registar_consumo(
        utilizador,
        pedido,
    ):
        raise PermissionDenied(
            "Não pode registar o consumo deste pedido."
        )

    _validar_formset(pedido, produtos_formset)
    produtos_formset.save()

    if observacoes_confirmacao:
        pedido.observacoes_confirmacao = (
            observacoes_confirmacao
        )
        pedido.save()

    registar_historico(
        pedido=pedido,
        acao=AcaoHistoricoCozinha.CONSUMO,
        profissional=utilizador,
    )

    return pedido


@transaction.atomic
def reabrir_pedido(
    pedido,
    utilizador,
    motivo,
):
    pedido = _bloquear_pedido(pedido)

    if not pode_reabrir_pedido(
        utilizador,
        pedido,
    ):
        raise PermissionDenied(
            "Não pode reabrir este pedido."
        )

    motivo = motivo.strip()

    if not motivo:
        raise ValidationError(
            "É obrigatório indicar o motivo da reabertura."
        )

    if pedido.estado != EstadoPedidoCozinha.ENVIADO:
        raise ValidationError(
            "Só é possível reabrir um pedido enviado "
            "que ainda não entrou em preparação."
        )

    estado_anterior = pedido.estado

    pedido.estado = EstadoPedidoCozinha.REABERTO
    pedido.reaberto_por = utilizador
    pedido.reaberto_em = timezone.now()
    pedido.motivo_reabertura = motivo

    pedido.full_clean()
    pedido.save()

    registar_historico(
        pedido=pedido,
        acao=AcaoHistoricoCozinha.REABERTO,
        profissional=utilizador,
        estado_anterior=estado_anterior,
        observacao=motivo,
    )

    return pedido
