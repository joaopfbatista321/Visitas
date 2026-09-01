from .models import (
    EstadoPedidoCozinha,
    UnidadeCozinha,
)


GRUPO_ENFERMAGEM = "UCCI_Enfermagem"
GRUPO_COZINHA = "UCCI_Cozinha"
GRUPO_COORDENACAO = "UCCI_Coordenacao"


def _nomes_grupos(utilizador):
    if not utilizador.is_authenticated:
        return set()

    return set(
        utilizador.groups.values_list(
            "name",
            flat=True,
        )
    )


def utilizador_e_enfermagem(utilizador):
    if not utilizador.is_authenticated:
        return False

    return (
        utilizador.is_superuser
        or GRUPO_ENFERMAGEM
        in _nomes_grupos(utilizador)
    )


def utilizador_e_cozinha(utilizador):
    if not utilizador.is_authenticated:
        return False

    return (
        utilizador.is_superuser
        or GRUPO_COZINHA
        in _nomes_grupos(utilizador)
    )


def utilizador_e_coordenacao(utilizador):
    if not utilizador.is_authenticated:
        return False

    return (
        utilizador.is_superuser
        or GRUPO_COORDENACAO
        in _nomes_grupos(utilizador)
    )


def utilizador_tem_acesso_cozinha(utilizador):
    if not utilizador.is_authenticated:
        return False

    grupos = _nomes_grupos(utilizador)

    return (
        utilizador.is_superuser
        or bool(
            grupos.intersection({
                GRUPO_ENFERMAGEM,
                GRUPO_COZINHA,
                GRUPO_COORDENACAO,
            })
        )
    )


def unidades_permitidas(utilizador):
    unidades = UnidadeCozinha.objects.filter(
        ativa=True
    ).order_by(
        "ordem",
        "nome",
    )

    if not utilizador_tem_acesso_cozinha(
        utilizador
    ):
        return unidades.none()

    # Todos os profissionais dos grupos autorizados
    # conseguem consultar todos os pisos ativos.
    return unidades


def utilizador_pertence_unidade(
    utilizador,
    unidade,
):
    if not utilizador_tem_acesso_cozinha(
        utilizador
    ):
        return False

    return unidade.ativa


def pode_ver_pedido(
    utilizador,
    pedido,
):
    # Enfermagem, Cozinha e Coordenação podem
    # consultar pedidos de qualquer piso.
    return utilizador_tem_acesso_cozinha(
        utilizador
    )


def pode_criar_pedido(
    utilizador,
    unidade,
):
    if not utilizador.is_authenticated:
        return False

    return (
        (
            utilizador_e_enfermagem(utilizador)
            or utilizador_e_coordenacao(utilizador)
        )
        and unidade.ativa
    )


def pode_editar_quantidades(
    utilizador,
    pedido,
):
    if not utilizador.is_authenticated:
        return False

    return (
        (
            utilizador_e_enfermagem(utilizador)
            or utilizador_e_coordenacao(utilizador)
        )
        and pedido.pode_editar_quantidades
    )


def pode_enviar_pedido(
    utilizador,
    pedido,
):
    return (
        pode_editar_quantidades(
            utilizador,
            pedido,
        )
        and pedido.estado
        in {
            EstadoPedidoCozinha.RASCUNHO,
            EstadoPedidoCozinha.REABERTO,
        }
    )


def pode_iniciar_preparacao(
    utilizador,
    pedido,
):
    return (
        (
            utilizador_e_cozinha(utilizador)
            or utilizador_e_coordenacao(utilizador)
        )
        and pedido.pode_iniciar_preparacao
    )


def pode_registar_entrega(
    utilizador,
    pedido,
):
    return (
        (
            utilizador_e_cozinha(utilizador)
            or utilizador_e_coordenacao(utilizador)
        )
        and pedido.estado
        == EstadoPedidoCozinha.EM_PREPARACAO
    )


def pode_confirmar_rececao(
    utilizador,
    pedido,
):
    if (
        pedido.estado
        != EstadoPedidoCozinha.ENTREGUE
    ):
        return False

    return (
        utilizador_e_enfermagem(utilizador)
        or utilizador_e_coordenacao(utilizador)
    )


def pode_registar_consumo(
    utilizador,
    pedido,
):
    if pedido.estado not in {
        EstadoPedidoCozinha.CONFIRMADO,
        EstadoPedidoCozinha.DIVERGENCIA,
    }:
        return False

    return (
        utilizador_e_enfermagem(utilizador)
        or utilizador_e_coordenacao(utilizador)
    )


def pode_reabrir_pedido(
    utilizador,
    pedido,
):
    return (
        utilizador_e_coordenacao(utilizador)
        and pedido.estado
        == EstadoPedidoCozinha.ENVIADO
        and not pedido.dentro_prazo_edicao
    )


def pode_consultar_relatorios(utilizador):
    return (
        utilizador_e_cozinha(utilizador)
        or utilizador_e_coordenacao(utilizador)
    )