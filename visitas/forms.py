from django import forms
from .models import Externo, Utente, Visita, TipoAlta, Isolamento, MovimentoFinanceiro


# Widgets para datas e datetimes em HTML5
class DateInput(forms.DateInput):
    input_type = "date"


class DateTimeInput(forms.DateTimeInput):
    input_type = "datetime-local"


class BaseStyledModelForm(forms.ModelForm):
    """
    Base que aplica 'form-control' a todos os campos (exceto checkboxes / radios).
    Fica tudo alinhado com o Bootstrap / Datta Able.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if not isinstance(widget, (forms.CheckboxInput, forms.RadioSelect)):
                css = widget.attrs.get("class", "")
                widget.attrs["class"] = (css + " form-control").strip()


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
        }


class UtenteSaidaForm(BaseStyledModelForm):
    """
    Form específico para registar a saída/alta do utente.
    Só mostra o que interessa na altura da alta.
    """
    class Meta:
        model = Utente
        fields = [
            "data_saida",
            "tipo_alta",
            "transferido_para",   # ← também aqui, mas só obrigatório se for transferência
        ]
        widgets = {
            "data_saida": DateInput(),
        }

    def clean(self):
        cleaned_data = super().clean()
        tipo_alta = cleaned_data.get("tipo_alta")
        transferido_para = cleaned_data.get("transferido_para")
        data_saida = cleaned_data.get("data_saida")

        # Obrigatório ter data de saída quando se regista alta
        if not data_saida:
            self.add_error("data_saida", "Indique a data de saída/alta do utente.")

        # Se for transferência, tem de indicar para onde
        if tipo_alta == TipoAlta.TRANSFERENCIA and not transferido_para:
            self.add_error(
                "transferido_para",
                "Indique para onde o utente foi transferido."
            )

        # Se NÃO for transferência, podemos limpar o campo
        if tipo_alta != TipoAlta.TRANSFERENCIA:
            cleaned_data["transferido_para"] = ""

        return cleaned_data


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
            "data_hora_entrada": DateTimeInput(),
            "data_hora_saida": DateTimeInput(),
            "observacoes": forms.Textarea(attrs={"rows": 4}),
        }


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
            "data_hora_entrada": DateTimeInput(),
            "data_hora_saida": DateTimeInput(),
            "observacoes": forms.Textarea(attrs={"rows": 4}),
        }


class IsolamentoForm(BaseStyledModelForm):
    class Meta:
        model = Isolamento
        fields = ["tipo", "data_inicio", "motivo", "observacoes"]
        widgets = {
            "data_inicio": DateTimeInput(),
            "observacoes": forms.Textarea(attrs={"rows": 4}),
        }

class MovimentoFinanceiroForm(forms.ModelForm):
    class Meta:
        model = MovimentoFinanceiro
        fields = ["tipo", "valor", "descricao"]

        widgets = {
            "tipo": forms.Select(attrs={"class": "form-select"}),
            "valor": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "min": "0.01"
            }),
            "descricao": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Justificação obrigatória"
            }),
        }