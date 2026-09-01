from django import forms
from django.forms import inlineformset_factory
from django.utils import timezone

from .models import (
    EstadoPedidoCozinha,
    LinhaProdutoPedido,
    LinhaRefeicaoPedido,
    PedidoCozinha,
    TipoPedidoCozinha,
    UnidadeCozinha,
)
from .permissoes import unidades_permitidas


class BasePedidoCozinhaForm(forms.ModelForm):
    tipo_pedido = None

    class Meta:
        model = PedidoCozinha
        fields = [
            "unidade",
            "data_servico",
            "observacoes_enfermagem",
        ]

        widgets = {
            "unidade": forms.Select(
                attrs={"class": "form-select"}
            ),
            "data_servico": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "class": "form-control",
                    "type": "date",
                },
            ),
            "observacoes_enfermagem": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": (
                        "Indicações gerais para a Cozinha."
                    ),
                }
            ),
        }

    def __init__(
        self,
        *args,
        utilizador=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.utilizador = utilizador

        if self.tipo_pedido:
            self.instance.tipo = self.tipo_pedido

        if utilizador:
            self.fields["unidade"].queryset = (
                unidades_permitidas(utilizador)
            )
        else:
            self.fields["unidade"].queryset = (
                UnidadeCozinha.objects.none()
            )

        if self.instance and self.instance.pk:
            self.fields["unidade"].disabled = True
            self.fields["data_servico"].disabled = True

    def clean_data_servico(self):
        data_servico = self.cleaned_data["data_servico"]

        if self.instance and self.instance.pk:
            return data_servico

        hoje = timezone.localdate()

        if data_servico < hoje:
            raise forms.ValidationError(
                "Não é possível criar um pedido para uma data anterior."
            )

        agora = timezone.localtime()

        if (
            self.tipo_pedido
            == TipoPedidoCozinha.REFEICOES
            and data_servico == hoje
            and agora.time()
            >= PedidoCozinha.HORA_LIMITE_EDICAO
        ):
            raise forms.ValidationError(
                "O prazo para criar o pedido de hoje terminou às 12:00."
            )

        return data_servico

    def clean(self):
        cleaned_data = super().clean()

        unidade = cleaned_data.get("unidade")
        data_servico = cleaned_data.get("data_servico")

        if not unidade or not data_servico:
            return cleaned_data

        pedidos = PedidoCozinha.objects.exclude(
            estado=EstadoPedidoCozinha.CANCELADO
        )

        if self.instance and self.instance.pk:
            pedidos = pedidos.exclude(
                pk=self.instance.pk
            )

        if self.tipo_pedido == TipoPedidoCozinha.REFEICOES:
            existe = pedidos.filter(
                unidade=unidade,
                data_servico=data_servico,
                tipo=TipoPedidoCozinha.REFEICOES,
            ).exists()

            if existe:
                self.add_error(
                    "unidade",
                    (
                        "Já existe um pedido de refeições "
                        "para este piso e esta data."
                    ),
                )

        if self.tipo_pedido == TipoPedidoCozinha.SUPLEMENTOS:
            estados_abertos = {
                EstadoPedidoCozinha.RASCUNHO,
                EstadoPedidoCozinha.ENVIADO,
                EstadoPedidoCozinha.REABERTO,
                EstadoPedidoCozinha.EM_PREPARACAO,
            }

            existe = pedidos.filter(
                unidade=unidade,
                tipo=TipoPedidoCozinha.SUPLEMENTOS,
                estado__in=estados_abertos,
            ).exists()

            if existe:
                self.add_error(
                    "unidade",
                    (
                        "Já existe um pedido de suplementos "
                        "em aberto para este piso. A Cozinha "
                        "deve terminá-lo antes de ser criado outro."
                    ),
                )

        return cleaned_data

    def save(self, commit=True):
        pedido = super().save(commit=False)
        pedido.tipo = self.tipo_pedido

        if commit:
            pedido.save()
            self.save_m2m()

        return pedido


class PedidoRefeicoesForm(BasePedidoCozinhaForm):
    tipo_pedido = TipoPedidoCozinha.REFEICOES


class PedidoSuplementosForm(BasePedidoCozinhaForm):
    tipo_pedido = TipoPedidoCozinha.SUPLEMENTOS


# Compatibilidade temporária com as views antigas. Na próxima
# etapa, as views passam a importar os dois formulários acima.
PedidoCozinhaForm = PedidoSuplementosForm


class QuantidadeFormMixin:
    campo_quantidade = None
    campo_origem = None
    campos_origem_alternativos = ()
    valor_predefinido = None
    passo = "0.01"

    def _valor_origem(self):
        nomes_campos = (
            self.campo_origem,
            *self.campos_origem_alternativos,
        )

        for nome_campo in nomes_campos:
            if not nome_campo:
                continue

            valor = getattr(
                self.instance,
                nome_campo,
                None,
            )

            if valor is not None:
                return valor

        return self.valor_predefinido

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        campo = self.fields[self.campo_quantidade]

        campo.required = False
        campo.widget.attrs.update(
            {
                "class": "form-control form-control-sm",
                "min": "0",
                "step": self.passo,
            }
        )

        if (
            not self.is_bound
            and self.instance
            and self.instance.pk
            and getattr(
                self.instance,
                self.campo_quantidade,
            ) is None
        ):
            valor_inicial = self._valor_origem()

            if valor_inicial is not None:
                # Num ModelForm, o valor atual do modelo fica em
                # self.initial. Alterar apenas campo.initial não
                # substitui corretamente um valor atual igual a None.
                self.initial[
                    self.campo_quantidade
                ] = valor_inicial

    def clean(self):
        cleaned_data = super().clean()

        quantidade = cleaned_data.get(
            self.campo_quantidade
        )

        quantidade_origem = self._valor_origem()

        if (
            quantidade_origem is not None
            and quantidade is None
        ):
            self.add_error(
                self.campo_quantidade,
                "Indique a quantidade.",
            )

        return cleaned_data


class ProdutoSolicitadoForm(forms.ModelForm):
    class Meta:
        model = LinhaProdutoPedido
        fields = [
            "quantidade_solicitada",
            "observacao_enfermagem",
        ]

        widgets = {
            "quantidade_solicitada": forms.NumberInput(
                attrs={
                    "class": "form-control form-control-sm",
                    "min": "0",
                    "step": "0.01",
                }
            ),
            "observacao_enfermagem": forms.TextInput(
                attrs={
                    "class": "form-control form-control-sm",
                    "placeholder": "Observação",
                }
            ),
        }


class RefeicaoSolicitadaForm(forms.ModelForm):
    class Meta:
        model = LinhaRefeicaoPedido
        fields = [
            "quantidade_solicitada",
            "observacao_enfermagem",
        ]

        widgets = {
            "quantidade_solicitada": forms.NumberInput(
                attrs={
                    "class": "form-control form-control-sm",
                    "min": "0",
                    "step": "1",
                }
            ),
            "observacao_enfermagem": forms.TextInput(
                attrs={
                    "class": "form-control form-control-sm",
                    "placeholder": "Observação",
                }
            ),
        }


class ProdutoPreparadoForm(
    QuantidadeFormMixin,
    forms.ModelForm,
):
    campo_quantidade = "quantidade_preparada"
    campo_origem = "quantidade_solicitada"
    passo = "0.01"

    class Meta:
        model = LinhaProdutoPedido
        fields = [
            "quantidade_preparada",
            "observacao_cozinha",
        ]

        widgets = {
            "quantidade_preparada": forms.NumberInput(),
            "observacao_cozinha": forms.TextInput(
                attrs={
                    "class": "form-control form-control-sm",
                    "placeholder": "Observação da Cozinha",
                }
            ),
        }


class RefeicaoPreparadaForm(
    QuantidadeFormMixin,
    forms.ModelForm,
):
    campo_quantidade = "quantidade_preparada"
    campo_origem = "quantidade_solicitada"
    passo = "1"

    class Meta:
        model = LinhaRefeicaoPedido
        fields = [
            "quantidade_preparada",
            "observacao_cozinha",
        ]

        widgets = {
            "quantidade_preparada": forms.NumberInput(),
            "observacao_cozinha": forms.TextInput(
                attrs={
                    "class": "form-control form-control-sm",
                    "placeholder": "Observação da Cozinha",
                }
            ),
        }


class ProdutoEntregueForm(
    QuantidadeFormMixin,
    forms.ModelForm,
):
    campo_quantidade = "quantidade_entregue"
    campo_origem = "quantidade_preparada"
    campos_origem_alternativos = (
        "quantidade_solicitada",
    )
    valor_predefinido = 0
    passo = "0.01"

    class Meta:
        model = LinhaProdutoPedido
        fields = [
            "quantidade_entregue",
            "observacao_cozinha",
        ]

        widgets = {
            "quantidade_entregue": forms.NumberInput(),
            "observacao_cozinha": forms.TextInput(
                attrs={
                    "class": "form-control form-control-sm",
                    "placeholder": "Observação da entrega",
                }
            ),
        }


class RefeicaoEntregueForm(
    QuantidadeFormMixin,
    forms.ModelForm,
):
    campo_quantidade = "quantidade_entregue"
    campo_origem = "quantidade_preparada"
    campos_origem_alternativos = (
        "quantidade_solicitada",
    )
    valor_predefinido = 0
    passo = "1"

    class Meta:
        model = LinhaRefeicaoPedido
        fields = [
            "quantidade_entregue",
            "observacao_cozinha",
        ]

        widgets = {
            "quantidade_entregue": forms.NumberInput(),
            "observacao_cozinha": forms.TextInput(
                attrs={
                    "class": "form-control form-control-sm",
                    "placeholder": "Observação da entrega",
                }
            ),
        }


class ProdutoRecebidoForm(
    QuantidadeFormMixin,
    forms.ModelForm,
):
    campo_quantidade = "quantidade_recebida"
    campo_origem = "quantidade_entregue"
    passo = "0.01"

    class Meta:
        model = LinhaProdutoPedido
        fields = [
            "quantidade_recebida",
            "observacao_confirmacao",
        ]

        widgets = {
            "quantidade_recebida": forms.NumberInput(),
            "observacao_confirmacao": forms.TextInput(
                attrs={
                    "class": "form-control form-control-sm",
                    "placeholder": (
                        "Indique faltas ou diferenças"
                    ),
                }
            ),
        }


class RefeicaoRecebidaForm(
    QuantidadeFormMixin,
    forms.ModelForm,
):
    campo_quantidade = "quantidade_recebida"
    campo_origem = "quantidade_entregue"
    passo = "1"

    class Meta:
        model = LinhaRefeicaoPedido
        fields = [
            "quantidade_recebida",
            "observacao_confirmacao",
        ]

        widgets = {
            "quantidade_recebida": forms.NumberInput(),
            "observacao_confirmacao": forms.TextInput(
                attrs={
                    "class": "form-control form-control-sm",
                    "placeholder": (
                        "Indique faltas ou diferenças"
                    ),
                }
            ),
        }


class ProdutoConsumidoForm(
    QuantidadeFormMixin,
    forms.ModelForm,
):
    campo_quantidade = "quantidade_consumida"
    campo_origem = "quantidade_recebida"
    passo = "0.01"

    class Meta:
        model = LinhaProdutoPedido
        fields = [
            "quantidade_consumida",
            "observacao_confirmacao",
        ]

        widgets = {
            "quantidade_consumida": forms.NumberInput(),
            "observacao_confirmacao": forms.TextInput(
                attrs={
                    "class": "form-control form-control-sm",
                    "placeholder": "Observação do consumo",
                }
            ),
        }


class RefeicaoConsumidaForm(
    QuantidadeFormMixin,
    forms.ModelForm,
):
    campo_quantidade = "quantidade_consumida"
    campo_origem = "quantidade_recebida"
    passo = "1"

    class Meta:
        model = LinhaRefeicaoPedido
        fields = [
            "quantidade_consumida",
            "observacao_confirmacao",
        ]

        widgets = {
            "quantidade_consumida": forms.NumberInput(),
            "observacao_confirmacao": forms.TextInput(
                attrs={
                    "class": "form-control form-control-sm",
                    "placeholder": "Observação do consumo",
                }
            ),
        }


class ObservacoesCozinhaForm(forms.ModelForm):
    class Meta:
        model = PedidoCozinha
        fields = ["observacoes_cozinha"]

        widgets = {
            "observacoes_cozinha": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                }
            ),
        }


class ObservacoesConfirmacaoForm(forms.ModelForm):
    class Meta:
        model = PedidoCozinha
        fields = ["observacoes_confirmacao"]

        widgets = {
            "observacoes_confirmacao": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                }
            ),
        }


class ReabrirPedidoForm(forms.Form):
    motivo = forms.CharField(
        label="Motivo da reabertura",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": (
                    "Explique por que motivo o pedido "
                    "deve ser reaberto para correção."
                ),
            }
        ),
    )


class FiltroPedidosCozinhaForm(forms.Form):
    tipo = forms.ChoiceField(
        label="Tipo de pedido",
        required=False,
        choices=[
            ("", "Todos os tipos"),
            *TipoPedidoCozinha.choices,
        ],
        widget=forms.Select(
            attrs={"class": "form-select"}
        ),
    )

    data_inicio = forms.DateField(
        label="De",
        required=False,
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date",
            }
        ),
    )

    data_fim = forms.DateField(
        label="Até",
        required=False,
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date",
            }
        ),
    )

    unidade = forms.ModelChoiceField(
        label="Unidade/piso",
        required=False,
        queryset=UnidadeCozinha.objects.none(),
        empty_label="Todas as unidades",
        widget=forms.Select(
            attrs={"class": "form-select"}
        ),
    )

    estado = forms.ChoiceField(
        label="Estado",
        required=False,
        choices=[],
        widget=forms.Select(
            attrs={"class": "form-select"}
        ),
    )

    def __init__(
        self,
        *args,
        utilizador=None,
        estados=(),
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        if utilizador:
            self.fields["unidade"].queryset = (
                unidades_permitidas(utilizador)
            )

        self.fields["estado"].choices = [
            ("", "Todos os estados"),
            *estados,
        ]

    def clean(self):
        cleaned_data = super().clean()

        data_inicio = cleaned_data.get("data_inicio")
        data_fim = cleaned_data.get("data_fim")

        if (
            data_inicio
            and data_fim
            and data_fim < data_inicio
        ):
            self.add_error(
                "data_fim",
                "A data final não pode ser anterior à inicial.",
            )

        return cleaned_data


class RelatorioMensalForm(forms.Form):
    tipo = forms.ChoiceField(
        label="Tipo de pedido",
        required=False,
        choices=[
            ("", "Todos os tipos"),
            *TipoPedidoCozinha.choices,
        ],
        widget=forms.Select(
            attrs={"class": "form-select"}
        ),
    )

    mes = forms.DateField(
        label="Mês",
        input_formats=["%Y-%m"],
        widget=forms.DateInput(
            format="%Y-%m",
            attrs={
                "class": "form-control",
                "type": "month",
            },
        ),
    )

    unidade = forms.ModelChoiceField(
        label="Unidade/piso",
        required=False,
        queryset=UnidadeCozinha.objects.none(),
        empty_label="Todas as unidades",
        widget=forms.Select(
            attrs={"class": "form-select"}
        ),
    )

    def __init__(
        self,
        *args,
        utilizador=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        if utilizador:
            self.fields["unidade"].queryset = (
                unidades_permitidas(utilizador)
            )


ProdutosSolicitadosFormSet = inlineformset_factory(
    PedidoCozinha,
    LinhaProdutoPedido,
    form=ProdutoSolicitadoForm,
    extra=0,
    can_delete=False,
)

RefeicoesSolicitadasFormSet = inlineformset_factory(
    PedidoCozinha,
    LinhaRefeicaoPedido,
    form=RefeicaoSolicitadaForm,
    extra=0,
    can_delete=False,
)

ProdutosPreparadosFormSet = inlineformset_factory(
    PedidoCozinha,
    LinhaProdutoPedido,
    form=ProdutoPreparadoForm,
    extra=0,
    can_delete=False,
)

RefeicoesPreparadasFormSet = inlineformset_factory(
    PedidoCozinha,
    LinhaRefeicaoPedido,
    form=RefeicaoPreparadaForm,
    extra=0,
    can_delete=False,
)

ProdutosEntreguesFormSet = inlineformset_factory(
    PedidoCozinha,
    LinhaProdutoPedido,
    form=ProdutoEntregueForm,
    extra=0,
    can_delete=False,
)

RefeicoesEntreguesFormSet = inlineformset_factory(
    PedidoCozinha,
    LinhaRefeicaoPedido,
    form=RefeicaoEntregueForm,
    extra=0,
    can_delete=False,
)

ProdutosRecebidosFormSet = inlineformset_factory(
    PedidoCozinha,
    LinhaProdutoPedido,
    form=ProdutoRecebidoForm,
    extra=0,
    can_delete=False,
)

RefeicoesRecebidasFormSet = inlineformset_factory(
    PedidoCozinha,
    LinhaRefeicaoPedido,
    form=RefeicaoRecebidaForm,
    extra=0,
    can_delete=False,
)

ProdutosConsumidosFormSet = inlineformset_factory(
    PedidoCozinha,
    LinhaProdutoPedido,
    form=ProdutoConsumidoForm,
    extra=0,
    can_delete=False,
)

RefeicoesConsumidasFormSet = inlineformset_factory(
    PedidoCozinha,
    LinhaRefeicaoPedido,
    form=RefeicaoConsumidaForm,
    extra=0,
    can_delete=False,
)
