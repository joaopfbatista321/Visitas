import calendar
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (
    FiltroPedidosCozinhaForm,
    ObservacoesConfirmacaoForm,
    ObservacoesCozinhaForm,
    PedidoRefeicoesForm,
    PedidoSuplementosForm,
    ProdutosConsumidosFormSet,
    ProdutosEntreguesFormSet,
    ProdutosPreparadosFormSet,
    ProdutosRecebidosFormSet,
    ProdutosSolicitadosFormSet,
    ReabrirPedidoForm,
    RefeicoesEntreguesFormSet,
    RefeicoesPreparadasFormSet,
    RefeicoesSolicitadasFormSet,
    RelatorioMensalForm,
)
from .models import (
    EstadoPedidoCozinha,
    LinhaProdutoPedido,
    LinhaRefeicaoPedido,
    PedidoCozinha,
    TipoPedidoCozinha,
)
from .permissoes import (
    pode_confirmar_rececao,
    pode_consultar_relatorios,
    pode_editar_quantidades,
    pode_enviar_pedido,
    pode_iniciar_preparacao,
    pode_reabrir_pedido,
    pode_registar_consumo,
    pode_registar_entrega,
    pode_ver_pedido,
    unidades_permitidas,
    utilizador_e_coordenacao,
    utilizador_e_cozinha,
    utilizador_e_enfermagem,
    utilizador_tem_acesso_cozinha,
)
from .servicos import (
    confirmar_rececao,
    criar_pedido,
    enviar_pedido,
    garantir_linhas_pedido,
    guardar_preparacao,
    guardar_quantidades_solicitadas,
    iniciar_preparacao,
    reabrir_pedido,
    registar_consumo,
    registar_entrega,
)


def _exigir_acesso(utilizador):
    if not utilizador_tem_acesso_cozinha(utilizador):
        raise PermissionDenied(
            "Não tem autorização para aceder à área da Cozinha."
        )


def _pedido(request, pk):
    pedido = get_object_or_404(
        PedidoCozinha.objects.select_related(
            "unidade",
            "criado_por",
            "enviado_por",
            "preparacao_por",
            "entregue_por",
            "confirmado_por",
            "reaberto_por",
        ).prefetch_related(
            "linhas_produtos__produto",
            "linhas_refeicoes__tipo_refeicao",
            "linhas_refeicoes__tipo_dieta",
            "historico__profissional",
        ),
        pk=pk,
    )

    if not pode_ver_pedido(request.user, pedido):
        raise PermissionDenied(
            "Não tem autorização para consultar este pedido."
        )

    return pedido


def _texto_validacao(erro):
    if hasattr(erro, "message_dict"):
        return " ".join(
            mensagem
            for mensagens in erro.message_dict.values()
            for mensagem in mensagens
        )

    return " ".join(erro.messages)


def _data_parametro(valor, predefinida):
    if not valor:
        return predefinida

    try:
        return datetime.strptime(valor, "%Y-%m-%d").date()
    except ValueError:
        return predefinida


def _tipo_parametro(valor, predefinido=None):
    if not valor:
        return predefinido

    valor = valor.upper()

    if valor in TipoPedidoCozinha.values:
        return valor

    return predefinido


def _formulario_classe(tipo):
    if tipo == TipoPedidoCozinha.REFEICOES:
        return PedidoRefeicoesForm

    return PedidoSuplementosForm


def _contexto_formset(pedido, formset):
    if pedido.tipo == TipoPedidoCozinha.REFEICOES:
        return {
            "linhas_formset": formset,
            "refeicoes_formset": formset,
            "produtos_formset": None,
        }

    return {
        "linhas_formset": formset,
        "refeicoes_formset": None,
        "produtos_formset": formset,
    }


@login_required
def lista_pedidos(request):
    _exigir_acesso(request.user)

    pedidos = (
        PedidoCozinha.objects
        .filter(unidade__in=unidades_permitidas(request.user))
        .select_related(
            "unidade",
            "criado_por",
            "enviado_por",
            "preparacao_por",
            "confirmado_por",
        )
    )

    dados_filtro = request.GET.copy()
    if dados_filtro.get("tipo"):
        dados_filtro["tipo"] = (
            _tipo_parametro(
                dados_filtro.get("tipo"),
                "",
            )
        )

    formulario = FiltroPedidosCozinhaForm(
        dados_filtro or None,
        utilizador=request.user,
        estados=EstadoPedidoCozinha.choices,
    )

    if formulario.is_valid():
        data_inicio = formulario.cleaned_data.get("data_inicio")
        data_fim = formulario.cleaned_data.get("data_fim")
        unidade = formulario.cleaned_data.get("unidade")
        estado = formulario.cleaned_data.get("estado")
        tipo = formulario.cleaned_data.get("tipo")

        if data_inicio:
            pedidos = pedidos.filter(data_servico__gte=data_inicio)
        if data_fim:
            pedidos = pedidos.filter(data_servico__lte=data_fim)
        if unidade:
            pedidos = pedidos.filter(unidade=unidade)
        if estado:
            pedidos = pedidos.filter(estado=estado)
        if tipo:
            pedidos = pedidos.filter(tipo=tipo)
    else:
        tipo = _tipo_parametro(
            request.GET.get("tipo")
        )

    pesquisa = request.GET.get("q", "").strip()
    if pesquisa:
        pedidos = pedidos.filter(
            Q(unidade__nome__icontains=pesquisa)
            | Q(unidade__codigo__icontains=pesquisa)
            | Q(observacoes_enfermagem__icontains=pesquisa)
            | Q(observacoes_cozinha__icontains=pesquisa)
        )

    hoje = timezone.localdate()
    pedidos_hoje = pedidos.filter(data_servico=hoje)

    context = {
        "formulario_filtros": formulario,
        "pedidos": pedidos.order_by("-data_servico", "unidade__ordem"),
        "pesquisa": pesquisa,
        "tipo_pedido": tipo,
        "total_hoje": pedidos_hoje.count(),
        "total_enviados": pedidos_hoje.filter(
            estado=EstadoPedidoCozinha.ENVIADO
        ).count(),
        "total_preparacao": pedidos_hoje.filter(
            estado=EstadoPedidoCozinha.EM_PREPARACAO
        ).count(),
        "total_divergencias": pedidos.filter(
            estado=EstadoPedidoCozinha.DIVERGENCIA
        ).count(),
        "pode_criar": (
            (
                utilizador_e_enfermagem(request.user)
                or utilizador_e_coordenacao(request.user)
            )
            and unidades_permitidas(request.user).exists()
        ),
        "pode_relatorios": pode_consultar_relatorios(request.user),
    }
    return render(request, "cozinha/lista_pedidos.html", context)


def _criar_pedido(request, tipo):
    _exigir_acesso(request.user)

    if not (
        utilizador_e_enfermagem(request.user)
        or utilizador_e_coordenacao(request.user)
    ):
        raise PermissionDenied(
            "Apenas a Enfermagem ou a Coordenação podem criar pedidos."
        )

    formulario_classe = _formulario_classe(tipo)
    formulario = formulario_classe(
        request.POST or None,
        utilizador=request.user,
    )

    if request.method == "POST" and formulario.is_valid():
        try:
            pedido = criar_pedido(formulario, request.user)
        except ValidationError as erro:
            formulario.add_error(None, _texto_validacao(erro))
        else:
            messages.success(
                request,
                (
                    f"{pedido.get_tipo_display()} criado. "
                    "Indique agora as quantidades."
                ),
            )
            return redirect("cozinha:editar_pedido", pk=pedido.pk)

    return render(
        request,
        "cozinha/form_pedido.html",
        {
            "formulario": formulario,
            "pedido": None,
            "tipo_pedido": tipo,
            "titulo_formulario": dict(
                TipoPedidoCozinha.choices
            )[tipo],
        },
    )


@login_required
def criar_pedido_refeicoes(request):
    return _criar_pedido(
        request,
        TipoPedidoCozinha.REFEICOES,
    )


@login_required
def criar_pedido_suplementos(request):
    return _criar_pedido(
        request,
        TipoPedidoCozinha.SUPLEMENTOS,
    )


@login_required
def criar_pedido_view(request):
    # Compatibilidade com o endereço antigo.
    tipo = _tipo_parametro(
        request.GET.get("tipo"),
        TipoPedidoCozinha.SUPLEMENTOS,
    )
    return _criar_pedido(request, tipo)


@login_required
def editar_pedido(request, pk):
    pedido = _pedido(request, pk)

    if not pode_editar_quantidades(request.user, pedido):
        raise PermissionDenied(
            "As quantidades deste pedido já não podem ser alteradas."
        )

    garantir_linhas_pedido(pedido)

    formulario_classe = _formulario_classe(pedido.tipo)
    formulario = formulario_classe(
        request.POST or None,
        instance=pedido,
        utilizador=request.user,
    )

    if pedido.tipo == TipoPedidoCozinha.REFEICOES:
        linhas = RefeicoesSolicitadasFormSet(
            request.POST or None,
            instance=pedido,
            prefix="refeicoes",
        )
    else:
        linhas = ProdutosSolicitadosFormSet(
            request.POST or None,
            instance=pedido,
            prefix="produtos",
        )

    if (
        request.method == "POST"
        and formulario.is_valid()
        and linhas.is_valid()
    ):
        try:
            pedido = guardar_quantidades_solicitadas(
                pedido,
                linhas,
                request.user,
                formulario.cleaned_data["observacoes_enfermagem"],
            )

            if request.POST.get("acao") == "enviar":
                pedido = enviar_pedido(pedido, request.user)
                mensagem = "Pedido enviado à Cozinha."
            else:
                mensagem = "Pedido guardado."
        except (PermissionDenied, ValidationError) as erro:
            if isinstance(erro, ValidationError):
                mensagem_erro = _texto_validacao(erro)
            else:
                mensagem_erro = str(erro)
            formulario.add_error(None, mensagem_erro)
        else:
            messages.success(request, mensagem)
            return redirect("cozinha:detalhe_pedido", pk=pedido.pk)

    context = {
        "formulario": formulario,
        "pedido": pedido,
        "tipo_pedido": pedido.tipo,
        "pode_enviar": pode_enviar_pedido(request.user, pedido),
    }
    context.update(_contexto_formset(pedido, linhas))

    return render(
        request,
        "cozinha/editar_pedido.html",
        context,
    )


@login_required
def detalhe_pedido(request, pk):
    pedido = _pedido(request, pk)

    context = {
        "pedido": pedido,
        "pode_editar": pode_editar_quantidades(request.user, pedido),
        "pode_enviar": pode_enviar_pedido(request.user, pedido),
        "pode_iniciar": pode_iniciar_preparacao(request.user, pedido),
        "pode_preparar": (
            pedido.estado == EstadoPedidoCozinha.EM_PREPARACAO
            and (
                utilizador_e_cozinha(request.user)
                or utilizador_e_coordenacao(request.user)
            )
        ),
        "pode_entregar": pode_registar_entrega(request.user, pedido),
        "pode_confirmar": (
            pedido.tipo == TipoPedidoCozinha.SUPLEMENTOS
            and pode_confirmar_rececao(request.user, pedido)
        ),
        "pode_consumo": (
            pedido.tipo == TipoPedidoCozinha.SUPLEMENTOS
            and pode_registar_consumo(request.user, pedido)
        ),
        "pode_reabrir": pode_reabrir_pedido(request.user, pedido),
    }
    return render(request, "cozinha/detalhe_pedido.html", context)


@require_POST
@login_required
def enviar_pedido_view(request, pk):
    pedido = _pedido(request, pk)
    try:
        pedido = enviar_pedido(pedido, request.user)
    except (PermissionDenied, ValidationError) as erro:
        mensagem = (
            _texto_validacao(erro)
            if isinstance(erro, ValidationError)
            else str(erro)
        )
        messages.error(request, mensagem)
    else:
        messages.success(request, "Pedido enviado à Cozinha.")
    return redirect("cozinha:detalhe_pedido", pk=pedido.pk)


@require_POST
@login_required
def iniciar_preparacao_view(request, pk):
    pedido = _pedido(request, pk)
    try:
        pedido = iniciar_preparacao(pedido, request.user)
    except (PermissionDenied, ValidationError) as erro:
        mensagem = (
            _texto_validacao(erro)
            if isinstance(erro, ValidationError)
            else str(erro)
        )
        messages.error(request, mensagem)
    else:
        messages.success(request, "Pedido colocado em preparação.")
    return redirect("cozinha:detalhe_pedido", pk=pedido.pk)


def _formset_fase(
    request,
    pedido,
    produtos_classe,
    refeicoes_classe,
):
    if pedido.tipo == TipoPedidoCozinha.REFEICOES:
        return refeicoes_classe(
            request.POST or None,
            instance=pedido,
            prefix="refeicoes",
        )

    return produtos_classe(
        request.POST or None,
        instance=pedido,
        prefix="produtos",
    )


@login_required
def preparar_pedido(request, pk):
    pedido = _pedido(request, pk)

    if not (
        pedido.estado == EstadoPedidoCozinha.EM_PREPARACAO
        and (
            utilizador_e_cozinha(request.user)
            or utilizador_e_coordenacao(request.user)
        )
    ):
        raise PermissionDenied("Não pode preparar este pedido.")

    linhas = _formset_fase(
        request,
        pedido,
        ProdutosPreparadosFormSet,
        RefeicoesPreparadasFormSet,
    )
    observacoes = ObservacoesCozinhaForm(
        request.POST or None,
        instance=pedido,
        prefix="observacoes",
    )

    if (
        request.method == "POST"
        and linhas.is_valid()
        and observacoes.is_valid()
    ):
        try:
            pedido = guardar_preparacao(
                pedido,
                linhas,
                request.user,
                observacoes.cleaned_data["observacoes_cozinha"],
            )
        except (PermissionDenied, ValidationError) as erro:
            messages.error(
                request,
                _texto_validacao(erro)
                if isinstance(erro, ValidationError)
                else str(erro),
            )
        else:
            messages.success(request, "Preparação atualizada.")
            return redirect("cozinha:detalhe_pedido", pk=pedido.pk)

    context = {
        "pedido": pedido,
        "observacoes_form": observacoes,
        "fase": "preparacao",
        "titulo": "Registar preparação",
        "texto_botao": "Guardar preparação",
    }
    context.update(_contexto_formset(pedido, linhas))

    return render(
        request,
        "cozinha/form_fase.html",
        context,
    )


@login_required
def entregar_pedido(request, pk):
    pedido = _pedido(request, pk)

    if not pode_registar_entrega(request.user, pedido):
        raise PermissionDenied("Não pode registar esta entrega.")

    linhas = _formset_fase(
        request,
        pedido,
        ProdutosEntreguesFormSet,
        RefeicoesEntreguesFormSet,
    )
    observacoes = ObservacoesCozinhaForm(
        request.POST or None,
        instance=pedido,
        prefix="observacoes",
    )

    if (
        request.method == "POST"
        and linhas.is_valid()
        and observacoes.is_valid()
    ):
        try:
            pedido = registar_entrega(
                pedido,
                linhas,
                request.user,
                observacoes.cleaned_data["observacoes_cozinha"],
            )
        except (PermissionDenied, ValidationError) as erro:
            messages.error(
                request,
                _texto_validacao(erro)
                if isinstance(erro, ValidationError)
                else str(erro),
            )
        else:
            messages.success(request, "Entrega registada.")
            return redirect("cozinha:detalhe_pedido", pk=pedido.pk)

    context = {
        "pedido": pedido,
        "observacoes_form": observacoes,
        "fase": "entrega",
        "titulo": "Registar entrega",
        "texto_botao": "Confirmar entrega",
    }
    context.update(_contexto_formset(pedido, linhas))

    return render(
        request,
        "cozinha/form_fase.html",
        context,
    )


@login_required
def confirmar_pedido(request, pk):
    pedido = _pedido(request, pk)

    if pedido.tipo != TipoPedidoCozinha.SUPLEMENTOS:
        raise PermissionDenied(
            "As refeições não necessitam de confirmação pela Enfermagem."
        )

    if not pode_confirmar_rececao(request.user, pedido):
        raise PermissionDenied("Não pode confirmar esta receção.")

    produtos = ProdutosRecebidosFormSet(
        request.POST or None,
        instance=pedido,
        prefix="produtos",
    )
    observacoes = ObservacoesConfirmacaoForm(
        request.POST or None,
        instance=pedido,
        prefix="observacoes",
    )

    if (
        request.method == "POST"
        and produtos.is_valid()
        and observacoes.is_valid()
    ):
        try:
            pedido = confirmar_rececao(
                pedido,
                produtos,
                request.user,
                observacoes.cleaned_data["observacoes_confirmacao"],
            )
        except (PermissionDenied, ValidationError) as erro:
            messages.error(
                request,
                _texto_validacao(erro)
                if isinstance(erro, ValidationError)
                else str(erro),
            )
        else:
            messages.success(request, "Receção confirmada.")
            return redirect("cozinha:detalhe_pedido", pk=pedido.pk)

    return render(
        request,
        "cozinha/form_fase.html",
        {
            "pedido": pedido,
            "produtos_formset": produtos,
            "refeicoes_formset": None,
            "linhas_formset": produtos,
            "observacoes_form": observacoes,
            "fase": "rececao",
            "titulo": "Confirmar quantidades recebidas",
            "texto_botao": "Confirmar receção",
        },
    )


@login_required
def consumo_pedido(request, pk):
    pedido = _pedido(request, pk)

    if pedido.tipo != TipoPedidoCozinha.SUPLEMENTOS:
        raise PermissionDenied(
            "O consumo separado aplica-se apenas aos suplementos."
        )

    if not pode_registar_consumo(request.user, pedido):
        raise PermissionDenied("Não pode registar este consumo.")

    produtos = ProdutosConsumidosFormSet(
        request.POST or None,
        instance=pedido,
        prefix="produtos",
    )
    observacoes = ObservacoesConfirmacaoForm(
        request.POST or None,
        instance=pedido,
        prefix="observacoes",
    )

    if (
        request.method == "POST"
        and produtos.is_valid()
        and observacoes.is_valid()
    ):
        try:
            pedido = registar_consumo(
                pedido,
                produtos,
                request.user,
                observacoes.cleaned_data["observacoes_confirmacao"],
            )
        except (PermissionDenied, ValidationError) as erro:
            messages.error(
                request,
                _texto_validacao(erro)
                if isinstance(erro, ValidationError)
                else str(erro),
            )
        else:
            messages.success(request, "Consumo registado.")
            return redirect("cozinha:detalhe_pedido", pk=pedido.pk)

    return render(
        request,
        "cozinha/form_fase.html",
        {
            "pedido": pedido,
            "produtos_formset": produtos,
            "refeicoes_formset": None,
            "linhas_formset": produtos,
            "observacoes_form": observacoes,
            "fase": "consumo",
            "titulo": "Registar consumo",
            "texto_botao": "Guardar consumo",
        },
    )


@login_required
def reabrir_pedido_view(request, pk):
    pedido = _pedido(request, pk)

    if not pode_reabrir_pedido(request.user, pedido):
        raise PermissionDenied("Não pode reabrir este pedido.")

    formulario = ReabrirPedidoForm(request.POST or None)

    if request.method == "POST" and formulario.is_valid():
        try:
            pedido = reabrir_pedido(
                pedido,
                request.user,
                formulario.cleaned_data["motivo"],
            )
        except (PermissionDenied, ValidationError) as erro:
            formulario.add_error(
                None,
                _texto_validacao(erro)
                if isinstance(erro, ValidationError)
                else str(erro),
            )
        else:
            messages.success(request, "Pedido reaberto para correção.")
            return redirect("cozinha:editar_pedido", pk=pedido.pk)

    return render(
        request,
        "cozinha/reabrir_pedido.html",
        {"pedido": pedido, "formulario": formulario},
    )


@login_required
def mapa_diario(request):
    _exigir_acesso(request.user)

    data = _data_parametro(
        request.GET.get("data"),
        timezone.localdate(),
    )

    tipo = _tipo_parametro(
        request.GET.get("tipo")
    )

    pedidos = (
        PedidoCozinha.objects
        .filter(
            data_servico=data,
            unidade__in=unidades_permitidas(request.user),
        )
        .exclude(estado=EstadoPedidoCozinha.CANCELADO)
        .select_related("unidade", "enviado_por", "preparacao_por")
        .prefetch_related(
            "linhas_produtos__produto",
            "linhas_refeicoes__tipo_refeicao",
            "linhas_refeicoes__tipo_dieta",
        )
        .order_by("unidade__ordem", "unidade__nome")
    )

    if tipo:
        pedidos = pedidos.filter(tipo=tipo)

    return render(
        request,
        "cozinha/mapa_diario.html",
        {
            "data": data,
            "pedidos": pedidos,
            "total_pedidos": pedidos.count(),
            "tipo_pedido": tipo,
        },
    )


@login_required
def relatorio_mensal(request):
    if not pode_consultar_relatorios(request.user):
        raise PermissionDenied(
            "Não tem autorização para consultar relatórios da Cozinha."
        )

    hoje = timezone.localdate()
    formulario = RelatorioMensalForm(
        request.GET or None,
        utilizador=request.user,
        initial={"mes": hoje.replace(day=1)},
    )

    mes = hoje.replace(day=1)
    unidade = None
    tipo = None
    if formulario.is_valid():
        mes = formulario.cleaned_data["mes"]
        unidade = formulario.cleaned_data.get("unidade")
        tipo = formulario.cleaned_data.get("tipo")

    ultimo_dia = calendar.monthrange(mes.year, mes.month)[1]
    data_inicio = mes.replace(day=1)
    data_fim = mes.replace(day=ultimo_dia)

    estados_contabilizados = {
        EstadoPedidoCozinha.ENVIADO,
        EstadoPedidoCozinha.EM_PREPARACAO,
        EstadoPedidoCozinha.ENTREGUE,
        EstadoPedidoCozinha.CONFIRMADO,
        EstadoPedidoCozinha.DIVERGENCIA,
    }

    pedidos = PedidoCozinha.objects.filter(
        data_servico__range=(data_inicio, data_fim),
        estado__in=estados_contabilizados,
        unidade__in=unidades_permitidas(request.user),
    )
    if unidade:
        pedidos = pedidos.filter(unidade=unidade)
    if tipo:
        pedidos = pedidos.filter(tipo=tipo)

    refeicoes = (
        LinhaRefeicaoPedido.objects
        .filter(
            pedido__in=pedidos,
            pedido__tipo=TipoPedidoCozinha.REFEICOES,
        )
        .values(
            "tipo_refeicao__nome",
            "tipo_refeicao__ordem",
            "tipo_dieta__nome",
            "tipo_dieta__ordem",
        )
        .annotate(
            solicitada=Sum("quantidade_solicitada"),
            entregue=Sum("quantidade_entregue"),
        )
        .order_by("tipo_refeicao__ordem", "tipo_dieta__ordem")
    )

    produtos = (
        LinhaProdutoPedido.objects
        .filter(
            pedido__in=pedidos,
            pedido__tipo=TipoPedidoCozinha.SUPLEMENTOS,
        )
        .values(
            "produto__nome",
            "produto__ordem",
            "produto__unidade_medida",
        )
        .annotate(
            solicitada=Sum("quantidade_solicitada"),
            recebida=Sum("quantidade_recebida"),
            consumida=Sum("quantidade_consumida"),
        )
        .order_by("produto__ordem", "produto__nome")
    )

    return render(
        request,
        "cozinha/relatorio_mensal.html",
        {
            "formulario": formulario,
            "mes": mes,
            "data_inicio": data_inicio,
            "data_fim": data_fim,
            "unidade": unidade,
            "tipo_pedido": tipo,
            "total_pedidos": pedidos.count(),
            "refeicoes": refeicoes,
            "produtos": produtos,
        },
    )
