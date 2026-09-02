from django import forms
from django.db.models import Q

from .models import (
    Condutor,
    Externo,
    Indisponibilidade,
    Isolamento,
    MeioTransporte,
    MovimentoFinanceiro,
    PagamentoMensalidade,
    PedidoTransporte,
    TipoAlta,
    Transporte,
    Utente,
    Viatura,
    Visita,
)

# ============================================================
# WIDGETS E FORMULÁRIO BASE
# ============================================================


class DateInput(forms.DateInput):
    input_type = "date"


class DateTimeInput(forms.DateTimeInput):
    input_type = "datetime-local"


class BaseStyledModelForm(forms.ModelForm):
    """
    Aplica as classes do Bootstrap/Datta Able a todos os campos.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = "form-check-input"
            elif not isinstance(widget, forms.RadioSelect):
                css = widget.attrs.get("class", "")
                widget.attrs["class"] = f"{css} form-control".strip()


# ============================================================
# UTENTES
# ============================================================


class UtenteForm(BaseStyledModelForm):
    class Meta:
        model = Utente
        fields = [
            "nome",
            "data_nascimento",
            "numero_processo",
            "numero_utente_sns",
            "genero",
            "tipo_internamento",
            "quarto",
            "data_entrada",
            "data_prevista_saida",
            "data_saida",
            "tipo_alta",
            "transferido_para",
            "visitas_restritas",
            "alerta_visitas",
            "observacoes",
            "saldo",
            "valor_caucao",
            "valor_dia",
            "paga_dias_ausencia",
            "contacto_emergencia1_nome",
            "contacto_emergencia1_telefone",
            "contacto_emergencia1_parentesco",
            "contacto_emergencia2_nome",
            "contacto_emergencia2_telefone",
            "contacto_emergencia2_parentesco",
        ]
        widgets = {
            "data_nascimento": DateInput(),
            "data_entrada": DateInput(),
            "data_prevista_saida": DateInput(),
            "data_saida": DateInput(),
            "observacoes": forms.Textarea(attrs={"rows": 4}),
            "alerta_visitas": forms.Textarea(attrs={"rows": 3}),
            "valor_dia": forms.NumberInput(
                attrs={"step": "0.01", "min": "0"}
            ),
            "valor_caucao": forms.NumberInput(
                attrs={"step": "0.01", "min": "0"}
            ),
        }


class UtenteSaidaForm(BaseStyledModelForm):
    """Formulário específico para registar a saída/alta do utente."""

    class Meta:
        model = Utente
        fields = ["data_saida", "tipo_alta", "transferido_para"]
        widgets = {"data_saida": DateInput()}

    def clean(self):
        cleaned_data = super().clean()
        tipo_alta = cleaned_data.get("tipo_alta")
        transferido_para = cleaned_data.get("transferido_para")
        data_saida = cleaned_data.get("data_saida")

        if not data_saida:
            self.add_error("data_saida", "Indique a data de saída/alta do utente.")

        if tipo_alta == TipoAlta.TRANSFERENCIA and not transferido_para:
            self.add_error(
                "transferido_para",
                "Indique para onde o utente foi transferido.",
            )

        if tipo_alta != TipoAlta.TRANSFERENCIA:
            cleaned_data["transferido_para"] = ""

        return cleaned_data


# ============================================================
# VISITAS, EXTERNOS E ISOLAMENTOS
# ============================================================


class VisitaForm(BaseStyledModelForm):
    class Meta:
        model = Visita
        fields = [
            "tipo_visitante",
            "nome_visitante",
            "documento_identificacao",
            "telefone",
            "parentesco",
            "data_hora_entrada",
            "data_hora_saida",
            "motivo",
            "observacoes",
        ]
        widgets = {
            "data_hora_entrada": DateTimeInput(format="%Y-%m-%dT%H:%M"),
            "data_hora_saida": DateTimeInput(format="%Y-%m-%dT%H:%M"),
            "observacoes": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["data_hora_entrada"].input_formats = ("%Y-%m-%dT%H:%M",)
        self.fields["data_hora_saida"].input_formats = ("%Y-%m-%dT%H:%M",)


class ExternoForm(BaseStyledModelForm):
    class Meta:
        model = Externo
        fields = [
            "tipo_externo",
            "nome",
            "empresa",
            "documento_identificacao",
            "telefone",
            "destino",
            "data_hora_entrada",
            "data_hora_saida",
            "motivo",
            "observacoes",
        ]
        widgets = {
            "data_hora_entrada": DateTimeInput(format="%Y-%m-%dT%H:%M"),
            "data_hora_saida": DateTimeInput(format="%Y-%m-%dT%H:%M"),
            "observacoes": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["data_hora_entrada"].input_formats = ("%Y-%m-%dT%H:%M",)
        self.fields["data_hora_saida"].input_formats = ("%Y-%m-%dT%H:%M",)


class IsolamentoForm(BaseStyledModelForm):
    class Meta:
        model = Isolamento
        fields = ["tipo", "data_inicio", "motivo", "observacoes"]
        widgets = {
            "data_inicio": DateTimeInput(format="%Y-%m-%dT%H:%M"),
            "observacoes": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["data_inicio"].input_formats = ("%Y-%m-%dT%H:%M",)


# ============================================================
# FINANCEIRO
# ============================================================


class MovimentoFinanceiroForm(forms.ModelForm):
    class Meta:
        model = MovimentoFinanceiro
        fields = ["tipo", "valor", "descricao"]
        widgets = {
            "tipo": forms.Select(attrs={"class": "form-select"}),
            "valor": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0.01"}
            ),
            "descricao": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Justificação obrigatória",
                }
            ),
        }


class ConfiguracaoMensalidadeUtenteForm(forms.ModelForm):
    class Meta:
        model = Utente
        fields = ["valor_dia", "paga_dias_ausencia"]
        widgets = {
            "valor_dia": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "paga_dias_ausencia": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }


class PagamentoMensalidadeForm(forms.ModelForm):
    class Meta:
        model = PagamentoMensalidade
        fields = ["valor", "data_pagamento", "observacoes"]
        widgets = {
            "valor": forms.NumberInput(
                attrs={
                    "class": "form-control form-control-sm",
                    "step": "0.01",
                    "min": "0.01",
                }
            ),
            "data_pagamento": DateInput(
                attrs={"class": "form-control form-control-sm"}
            ),
            "observacoes": forms.TextInput(
                attrs={
                    "class": "form-control form-control-sm",
                    "placeholder": "Observações (opcional)",
                }
            ),
        }


# ============================================================
# TRANSPORTES DE UTENTES
# ============================================================

class PedidoTransporteForm(BaseStyledModelForm):
    class Meta:
        model = PedidoTransporte
        fields = [
            "utente",
            "tipo_deslocacao",
            "motivo",
            "destino",
            "data_hora_consulta",
            "acompanhante_nome",
            "acompanhante_contacto",
            "necessita_cadeira_rodas",
            "necessita_maca",
            "necessita_oxigenio",
            "outras_necessidades",
            "observacoes",

            # Informação opcional
            "data_hora_saida",
            "data_hora_regresso_previsto",
            "meio_transporte",
            "viatura",
            "condutor",
            "entidade_transporte",
        ]

        widgets = {
            "data_hora_consulta": DateTimeInput(
                format="%Y-%m-%dT%H:%M"
            ),
            "data_hora_saida": DateTimeInput(
                format="%Y-%m-%dT%H:%M"
            ),
            "data_hora_regresso_previsto": DateTimeInput(
                format="%Y-%m-%dT%H:%M"
            ),
            "observacoes": forms.Textarea(
                attrs={"rows": 4}
            ),
        }

        help_texts = {
            "data_hora_saida": (
                "Opcional. Preencha apenas se já souber a hora prevista."
            ),
            "data_hora_regresso_previsto": (
                "Opcional. A Receção poderá completar este campo."
            ),
            "meio_transporte": (
                "Opcional. A Receção poderá definir o meio de transporte."
            ),
            "viatura": (
                "Opcional. Selecione apenas se a viatura já estiver definida."
            ),
            "condutor": (
                "Opcional. Selecione apenas se o condutor já estiver definido."
            ),
            "entidade_transporte": (
                "Ex.: Bombeiros, táxi, familiar ou outra entidade."
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        utente_atual = getattr(self.instance, "utente_id", None)
        viatura_atual = getattr(self.instance, "viatura_id", None)
        condutor_atual = getattr(self.instance, "condutor_id", None)

        self.fields["utente"].queryset = Utente.objects.filter(
            Q(data_saida__isnull=True) | Q(pk=utente_atual)
        ).order_by("nome")

        self.fields["viatura"].queryset = Viatura.objects.filter(
            Q(ativo=True) | Q(pk=viatura_atual)
        ).order_by("matricula")

        self.fields["condutor"].queryset = Condutor.objects.filter(
            Q(ativo=True) | Q(pk=condutor_atual)
        ).order_by("nome")

        for nome in (
            "data_hora_consulta",
            "data_hora_saida",
            "data_hora_regresso_previsto",
        ):
            self.fields[nome].input_formats = (
                "%Y-%m-%dT%H:%M",
            )

    def clean(self):
        cleaned_data = super().clean()
        meio_transporte = cleaned_data.get("meio_transporte")

        if not meio_transporte:
            cleaned_data["viatura"] = None
            cleaned_data["condutor"] = None
            cleaned_data["entidade_transporte"] = ""

        elif meio_transporte != MeioTransporte.INSTITUICAO:
            cleaned_data["viatura"] = None
            cleaned_data["condutor"] = None

        else:
            cleaned_data["entidade_transporte"] = ""

        return cleaned_data

class ValidarPedidoTransporteForm(PedidoTransporteForm):
    class Meta(PedidoTransporteForm.Meta):
        fields = PedidoTransporteForm.Meta.fields + [
            "observacoes_recepcao",
        ]

        widgets = {
            **PedidoTransporteForm.Meta.widgets,
            "observacoes_recepcao": forms.Textarea(
                attrs={"rows": 3}
            ),
        }

        help_texts = {
            **PedidoTransporteForm.Meta.help_texts,
            "observacoes_recepcao": (
                "Informação interna sobre a validação do pedido."
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Estes campos passam a ser obrigatórios
        # quando a Receção valida o pedido.
        for nome in (
            "motivo",
            "destino",
            "data_hora_saida",
            "data_hora_regresso_previsto",
            "meio_transporte",
        ):
            self.fields[nome].required = True

    def clean(self):
        cleaned_data = super().clean()

        meio_transporte = cleaned_data.get(
            "meio_transporte"
        )

        viatura = cleaned_data.get(
            "viatura"
        )

        condutor = cleaned_data.get(
            "condutor"
        )

        entidade_transporte = cleaned_data.get(
            "entidade_transporte"
        )

        data_hora_saida = cleaned_data.get(
            "data_hora_saida"
        )

        data_hora_consulta = cleaned_data.get(
            "data_hora_consulta"
        )

        data_hora_regresso = cleaned_data.get(
            "data_hora_regresso_previsto"
        )

        # Transporte interno
        if meio_transporte == MeioTransporte.INSTITUICAO:
            if not viatura:
                self.add_error(
                    "viatura",
                    "Selecione a viatura da instituição.",
                )

            if not condutor:
                self.add_error(
                    "condutor",
                    "Selecione o condutor.",
                )

        # Transporte externo
        elif meio_transporte:
            if not entidade_transporte:
                self.add_error(
                    "entidade_transporte",
                    (
                        "Indique a entidade ou pessoa responsável "
                        "pelo transporte."
                    ),
                )

        # Validação dos horários
        if (
            data_hora_saida
            and data_hora_regresso
            and data_hora_regresso <= data_hora_saida
        ):
            self.add_error(
                "data_hora_regresso_previsto",
                (
                    "O regresso previsto tem de ser posterior "
                    "à saída."
                ),
            )

        if (
            data_hora_consulta
            and data_hora_saida
            and data_hora_consulta < data_hora_saida
        ):
            self.add_error(
                "data_hora_consulta",
                (
                    "A consulta/exame não pode ser anterior "
                    "à saída prevista."
                ),
            )

        if (
            data_hora_consulta
            and data_hora_regresso
            and data_hora_consulta > data_hora_regresso
        ):
            self.add_error(
                "data_hora_consulta",
                (
                    "A consulta/exame não pode ser posterior "
                    "ao regresso previsto."
                ),
            )

        return cleaned_data

class TransporteForm(BaseStyledModelForm):
    class Meta:
        model = Transporte
        fields = [
            "utente",
            "tipo_deslocacao",
            "motivo",
            "destino",
            "data_hora_saida",
            "data_hora_consulta",
            "data_hora_regresso_previsto",
            "meio_transporte",
            "viatura",
            "condutor",
            "entidade_transporte",
            "acompanhante_nome",
            "acompanhante_contacto",
            "necessita_cadeira_rodas",
            "necessita_maca",
            "necessita_oxigenio",
            "outras_necessidades",
            "observacoes",
        ]
        widgets = {
            "data_hora_saida": DateTimeInput(format="%Y-%m-%dT%H:%M"),
            "data_hora_consulta": DateTimeInput(format="%Y-%m-%dT%H:%M"),
            "data_hora_regresso_previsto": DateTimeInput(format="%Y-%m-%dT%H:%M"),
            "observacoes": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        utente_atual = getattr(self.instance, "utente_id", None)
        viatura_atual = getattr(self.instance, "viatura_id", None)
        condutor_atual = getattr(self.instance, "condutor_id", None)

        self.fields["utente"].queryset = Utente.objects.filter(
            Q(data_saida__isnull=True) | Q(pk=utente_atual)
        ).order_by("nome")
        self.fields["viatura"].queryset = Viatura.objects.filter(
            Q(ativo=True) | Q(pk=viatura_atual)
        ).order_by("matricula")
        self.fields["condutor"].queryset = Condutor.objects.filter(
            Q(ativo=True) | Q(pk=condutor_atual)
        ).order_by("nome")

        for nome in (
            "data_hora_saida",
            "data_hora_consulta",
            "data_hora_regresso_previsto",
        ):
            self.fields[nome].input_formats = ("%Y-%m-%dT%H:%M",)

    def clean(self):
        cleaned_data = super().clean()
        meio_transporte = cleaned_data.get("meio_transporte")

        if meio_transporte != MeioTransporte.INSTITUICAO:
            cleaned_data["viatura"] = None
            cleaned_data["condutor"] = None
            self.instance.viatura = None
            self.instance.condutor = None
        else:
            cleaned_data["entidade_transporte"] = ""
            self.instance.entidade_transporte = ""

        return cleaned_data


class ViaturaForm(BaseStyledModelForm):
    class Meta:
        model = Viatura
        fields = [
            "matricula",
            "designacao",
            "tipo",
            "marca",
            "modelo",
            "numero_lugares",
            "adaptada_cadeira_rodas",
            "permite_maca",
            "validade_seguro",
            "validade_inspecao",
            "ativo",
            "observacoes",
        ]
        widgets = {
            "validade_seguro": DateInput(),
            "validade_inspecao": DateInput(),
            "observacoes": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_matricula(self):
        matricula = self.cleaned_data["matricula"]
        return matricula.strip().upper().replace(" ", "-")


class CondutorForm(BaseStyledModelForm):
    class Meta:
        model = Condutor
        fields = [
            "nome",
            "numero_mecanografico",
            "telefone",
            "categoria_carta",
            "numero_carta",
            "validade_carta",
            "ativo",
            "observacoes",
        ]
        widgets = {
            "validade_carta": DateInput(),
            "observacoes": forms.Textarea(attrs={"rows": 3}),
        }


class IndisponibilidadeForm(BaseStyledModelForm):
    class Meta:
        model = Indisponibilidade
        fields = [
            "viatura",
            "condutor",
            "inicio",
            "fim",
            "motivo",
            "observacoes",
        ]
        widgets = {
            "inicio": DateTimeInput(format="%Y-%m-%dT%H:%M"),
            "fim": DateTimeInput(format="%Y-%m-%dT%H:%M"),
            "observacoes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["viatura"].queryset = Viatura.objects.order_by("matricula")
        self.fields["condutor"].queryset = Condutor.objects.order_by("nome")
        self.fields["inicio"].input_formats = ("%Y-%m-%dT%H:%M",)
        self.fields["fim"].input_formats = ("%Y-%m-%dT%H:%M",)
