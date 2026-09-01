from django import forms
from django.contrib.auth import get_user_model

from cozinha.models import EstadoPedidoCozinha, TipoPedidoCozinha, UnidadeCozinha
from enfermagem.models import GravidadeQueda, TipoRegistoEnfermagem, TurnoEnfermagem
from fisioterapia.models import EstadoSessaoFisioterapia, TipoSessaoFisioterapia
from visitas.models import (
    EstadoTransporte,
    Genero,
    MeioTransporte,
    Piso,
    TipoDeslocacao,
    TipoInternamento,
    TipoVisitante,
)


User = get_user_model()


class FiltroPeriodoForm(forms.Form):
    data_inicio = forms.DateField(
        label="De",
        required=False,
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
    )
    data_fim = forms.DateField(
        label="Até",
        required=False,
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            classe = "form-select" if isinstance(campo.widget, forms.Select) else "form-control"
            campo.widget.attrs.setdefault("class", classe)

    def clean(self):
        dados = super().clean()
        inicio = dados.get("data_inicio")
        fim = dados.get("data_fim")
        if inicio and fim and inicio > fim:
            raise forms.ValidationError(
                "A data inicial não pode ser posterior à data final."
            )
        if inicio and fim and (fim - inicio).days > 730:
            raise forms.ValidationError(
                "Selecione um período máximo de dois anos para manter os gráficos rápidos."
            )
        return dados


class FiltroPeriodoPisoForm(FiltroPeriodoForm):
    piso = forms.ChoiceField(
        label="Piso",
        required=False,
        choices=[("", "Todos os pisos"), *Piso.choices],
    )


class FiltroUtentesForm(FiltroPeriodoPisoForm):
    tipo_internamento = forms.ChoiceField(
        label="Internamento",
        required=False,
        choices=[("", "Todos os internamentos"), *TipoInternamento.choices],
    )
    genero = forms.ChoiceField(
        label="Género",
        required=False,
        choices=[("", "Todos"), *Genero.choices],
    )
    situacao = forms.ChoiceField(
        label="Situação",
        required=False,
        choices=[
            ("", "Ativos e altas"),
            ("ATIVO", "Apenas ativos"),
            ("ALTA", "Apenas com alta"),
        ],
    )


class FiltroVisitasForm(FiltroPeriodoPisoForm):
    periodo_rapido = forms.ChoiceField(
        label="Período rápido",
        required=False,
        choices=[
            ("", "Personalizado"),
            ("SEMANA", "Semana atual"),
            ("MES", "Mês atual"),
            ("ANO", "Ano atual"),
        ],
    )
    tipo_visitante = forms.ChoiceField(
        label="Visitante",
        required=False,
        choices=[("", "Todos os tipos"), *TipoVisitante.choices],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_fields(
            [
                "periodo_rapido",
                "data_inicio",
                "data_fim",
                "piso",
                "tipo_visitante",
            ]
        )


class FiltroTransportesForm(FiltroPeriodoPisoForm):
    estado = forms.ChoiceField(
        label="Estado",
        required=False,
        choices=[("", "Todos os estados"), *EstadoTransporte.choices],
    )
    meio = forms.ChoiceField(
        label="Meio",
        required=False,
        choices=[("", "Todos os meios"), *MeioTransporte.choices],
    )
    tipo_deslocacao = forms.ChoiceField(
        label="Deslocação",
        required=False,
        choices=[("", "Todos os tipos"), *TipoDeslocacao.choices],
    )


class FiltroEnfermagemForm(FiltroPeriodoPisoForm):
    turno = forms.ChoiceField(
        label="Turno",
        required=False,
        choices=[("", "Todos os turnos"), *TurnoEnfermagem.choices],
    )
    tipo_registo = forms.ModelChoiceField(
        label="Tipo de registo",
        required=False,
        queryset=TipoRegistoEnfermagem.objects.none(),
        empty_label="Todos os tipos",
    )
    gravidade = forms.ChoiceField(
        label="Gravidade da queda",
        required=False,
        choices=[("", "Todas"), *GravidadeQueda.choices],
    )
    profissional = forms.ModelChoiceField(
        label="Profissional",
        required=False,
        queryset=User.objects.none(),
        empty_label="Todos os profissionais",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tipo_registo"].queryset = TipoRegistoEnfermagem.objects.filter(
            ativo=True
        ).order_by("ordem", "nome")
        self.fields["profissional"].queryset = User.objects.filter(
            groups__name="UCCI_Enfermagem", is_active=True
        ).distinct().order_by("first_name", "last_name", "username")


class FiltroFisioterapiaForm(FiltroPeriodoPisoForm):
    estado = forms.ChoiceField(
        label="Estado",
        required=False,
        choices=[("", "Todos os estados"), *EstadoSessaoFisioterapia.choices],
    )
    tipo = forms.ChoiceField(
        label="Sessão",
        required=False,
        choices=[("", "Individual e grupo"), *TipoSessaoFisioterapia.choices],
    )
    profissional = forms.ModelChoiceField(
        label="Fisioterapeuta",
        required=False,
        queryset=User.objects.none(),
        empty_label="Todos os profissionais",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["profissional"].queryset = User.objects.filter(
            groups__name="UCCI_Fisioterapia", is_active=True
        ).distinct().order_by("first_name", "last_name", "username")


class FiltroCozinhaForm(FiltroPeriodoForm):
    unidade = forms.ModelChoiceField(
        label="Unidade/piso",
        required=False,
        queryset=UnidadeCozinha.objects.none(),
        empty_label="Todas as unidades",
    )
    tipo = forms.ChoiceField(
        label="Pedido",
        required=False,
        choices=[("", "Refeições e suplementos"), *TipoPedidoCozinha.choices],
    )
    estado = forms.ChoiceField(
        label="Estado",
        required=False,
        choices=[("", "Todos os estados"), *EstadoPedidoCozinha.choices],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["unidade"].queryset = UnidadeCozinha.objects.filter(
            ativa=True
        ).order_by("ordem", "nome")


class FiltroFinanceiroForm(FiltroPeriodoPisoForm):
    tipo = forms.ChoiceField(
        label="Movimento",
        required=False,
        choices=[
            ("", "Entradas e saídas"),
            ("ENTRADA", "Entradas"),
            ("SAIDA", "Saídas"),
        ],
    )
