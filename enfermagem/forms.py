from django import forms
from django.db.models import Q
from django.utils import timezone

from .models import (
    AcompanhamentoQueda,
    AtividadeQueda,
    AusenciaUtente,
    DispositivoAuxilio,
    EstadoAusenciaUtente,
    EstadoGradesLaterais,
    EstadoMedidasPreventivas,
    EstadoNotificacaoFamiliar,
    EstadoNotificacaoInstitucional,
    EstadoReavaliacaoMorse,
    FatorContribuinteQueda,
    GravidadeQueda,
    IntervencaoQueda,
    LesaoIdentificada,
    LocalizacaoLesao,
    MedidaCorretivaQueda,
    OpcaoSimNao,
    RegistoEnfermagem,
    RegistoQueda,
    TipoRegistoEnfermagem,
    TipoAusenciaUtente,
)


class AusenciaUtenteForm(forms.ModelForm):
    class Meta:
        model = AusenciaUtente
        fields = [
            "tipo",
            "data_hora_inicio",
            "data_hora_fim_prevista",
            "destino",
            "motivo",
            "observacoes",
        ]

        widgets = {
            "tipo": forms.Select(
                attrs={"class": "form-select"}
            ),
            "data_hora_inicio": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                },
            ),
            "data_hora_fim_prevista": (
                forms.DateTimeInput(
                    format="%Y-%m-%dT%H:%M",
                    attrs={
                        "class": "form-control",
                        "type": "datetime-local",
                    },
                )
            ),
            "destino": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "Ex.: Serviço de Urgência ou hospital"
                    ),
                }
            ),
            "motivo": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": (
                        "Indique o motivo da ausência."
                    ),
                }
            ),
            "observacoes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.is_bound and not self.instance.pk:
            self.fields["data_hora_inicio"].initial = (
                timezone.localtime().replace(
                    second=0,
                    microsecond=0,
                )
            )

    def clean(self):
        cleaned_data = super().clean()

        inicio = cleaned_data.get("data_hora_inicio")
        fim_previsto = cleaned_data.get(
            "data_hora_fim_prevista"
        )

        if (
            inicio
            and fim_previsto
            and fim_previsto <= inicio
        ):
            self.add_error(
                "data_hora_fim_prevista",
                (
                    "O regresso previsto tem de ser "
                    "posterior à saída."
                ),
            )

        return cleaned_data


class RegressoAusenciaForm(forms.Form):
    data_hora_regresso = forms.DateTimeField(
        label="Data e hora do regresso",
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(
            format="%Y-%m-%dT%H:%M",
            attrs={
                "class": "form-control",
                "type": "datetime-local",
            },
        ),
    )

    observacoes = forms.CharField(
        label="Observações do regresso",
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
            }
        ),
    )

    def __init__(
        self,
        *args,
        ausencia=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.ausencia = ausencia

        if not self.is_bound:
            self.fields["data_hora_regresso"].initial = (
                timezone.localtime().replace(
                    second=0,
                    microsecond=0,
                )
            )

    def clean_data_hora_regresso(self):
        momento = self.cleaned_data[
            "data_hora_regresso"
        ]

        if (
            self.ausencia
            and momento
            < self.ausencia.data_hora_inicio
        ):
            raise forms.ValidationError(
                "O regresso não pode ser anterior à saída."
            )

        if momento > timezone.now():
            raise forms.ValidationError(
                "O regresso não pode ser registado no futuro."
            )

        return momento


class FiltroAusenciasForm(forms.Form):
    q = forms.CharField(
        label="Pesquisa",
        required=False,
        widget=forms.TextInput(
            attrs={
                "type": "search",
                "class": "form-control",
                "placeholder": "Nome ou número de processo",
            }
        ),
    )

    estado = forms.ChoiceField(
        label="Estado",
        required=False,
        choices=[
            ("", "Todos os estados"),
            *EstadoAusenciaUtente.choices,
        ],
        widget=forms.Select(
            attrs={"class": "form-select"}
        ),
    )

    tipo = forms.ChoiceField(
        label="Tipo",
        required=False,
        choices=[
            ("", "Todos os tipos"),
            *TipoAusenciaUtente.choices,
        ],
        widget=forms.Select(
            attrs={"class": "form-select"}
        ),
    )

    piso = forms.ChoiceField(
        label="Piso",
        required=False,
        choices=[("", "Todos os pisos")],
        widget=forms.Select(
            attrs={"class": "form-select"}
        ),
    )

    def __init__(
        self,
        *args,
        pisos=(),
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.fields["piso"].choices = [
            ("", "Todos os pisos"),
            *[(valor, nome) for valor, nome in pisos],
        ]


class RegistoEnfermagemForm(forms.ModelForm):
    class Meta:
        model = RegistoEnfermagem
        fields = [
            "data_registo",
            "turno",
            "tipo_registo",
            "observacao",
            "cuidados_realizados",
            "resposta_utente",
            "plano_cuidados",
            "visibilidade",
        ]

        widgets = {
            "data_registo": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                },
            ),
            "turno": forms.Select(
                attrs={"class": "form-select"}
            ),
            "tipo_registo": forms.Select(
                attrs={"class": "form-select"}
            ),
            "observacao": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                }
            ),
            "cuidados_realizados": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                }
            ),
            "resposta_utente": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                }
            ),
            "plano_cuidados": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                }
            ),
            "visibilidade": forms.Select(
                attrs={"class": "form-select"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        tipos = TipoRegistoEnfermagem.objects.filter(
            ativo=True,
        ).exclude(
            codigo="queda",
        )

        if self.instance and self.instance.pk:
            tipos = TipoRegistoEnfermagem.objects.filter(
                Q(ativo=True)
                | Q(pk=self.instance.tipo_registo_id)
            ).exclude(
                codigo="queda",
            )

        self.fields["tipo_registo"].queryset = (
            tipos.order_by("ordem", "nome")
        )

        if not self.is_bound and not self.instance.pk:
            self.fields["data_registo"].initial = (
                timezone.localtime().replace(
                    second=0,
                    microsecond=0,
                )
            )


class CabecalhoRegistoQuedaForm(forms.ModelForm):
    class Meta:
        model = RegistoEnfermagem
        fields = [
            "data_registo",
            "turno",
            "visibilidade",
        ]

        widgets = {
            "data_registo": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                },
            ),
            "turno": forms.Select(
                attrs={"class": "form-select"}
            ),
            "visibilidade": forms.Select(
                attrs={"class": "form-select"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["turno"].required = True

        if not self.is_bound and not self.instance.pk:
            self.fields["data_registo"].initial = (
                timezone.localtime().replace(
                    second=0,
                    microsecond=0,
                )
            )


class RegistoQuedaForm(forms.ModelForm):
    lesoes_identificadas = forms.MultipleChoiceField(
        label="Lesões identificadas",
        choices=LesaoIdentificada.choices,
        required=True,
        widget=forms.CheckboxSelectMultiple(
            
        ),
    )

    localizacoes_lesao = forms.MultipleChoiceField(
        label="Localização das lesões",
        choices=LocalizacaoLesao.choices,
        required=False,
        widget=forms.CheckboxSelectMultiple(
            
        ),
    )

    fatores_contribuintes = forms.MultipleChoiceField(
        label="Fatores contribuintes",
        choices=FatorContribuinteQueda.choices,
        required=False,
        widget=forms.CheckboxSelectMultiple(
           
        ),
    )

    intervencoes_realizadas = forms.MultipleChoiceField(
        label="Intervenções efetuadas",
        choices=IntervencaoQueda.choices,
        required=True,
        widget=forms.CheckboxSelectMultiple(
            
        ),
    )

    medidas_corretivas = forms.MultipleChoiceField(
        label="Medidas corretivas implementadas",
        choices=MedidaCorretivaQueda.choices,
        required=False,
        widget=forms.CheckboxSelectMultiple(
           
        ),
    )

    class Meta:
        model = RegistoQueda
        fields = [
            # Identificação complementar
            "servico_unidade",
            "diagnostico_principal",
            "medico_assistente",

            # Dados da ocorrência
            "data_hora_queda",
            "local_queda",
            "local_detalhe",

            # Classificação
            "tipo_queda",
            "gravidade",
            "lesoes_identificadas",
            "lesao_outra",
            "localizacoes_lesao",
            "localizacao_outra",

            # Circunstâncias
            "doente_estava",
            "atividade_no_momento",
            "atividade_outra",
            "fatores_contribuintes",
            "fator_contribuinte_outro",
            "grades_laterais",
            "dispositivo_auxilio",
            "dispositivo_auxilio_outro",

            # Morse anterior
            "morse_aplicada",
            "score_morse_previo",
            "medidas_preventivas_implementadas",

            # Resposta imediata
            "intervencoes_realizadas",
            "intervencao_outra",
            "medico_notificado",
            "medico_notificado_em",
            "medico_nao_notificado_justificacao",
            "familiar_notificado",
            "familiar_notificado_em",
            "descricao_ocorrencia",

            # Seguimento
            "reavaliacao_morse_estado",
            "score_morse_pos",
            "medidas_corretivas",
            "medida_corretiva_outra",
            "observacoes",

            # Notificação institucional
            "notificacao_institucional_estado",
            "data_notificacao_institucional",
        ]

        widgets = {
            "servico_unidade": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "diagnostico_principal": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                }
            ),
            "medico_assistente": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "data_hora_queda": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                },
            ),
            "local_queda": forms.Select(
                attrs={"class": "form-select"}
            ),
            "local_detalhe": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "tipo_queda": forms.Select(
                attrs={"class": "form-select"}
            ),
            "gravidade": forms.Select(
                attrs={"class": "form-select"}
            ),
            "lesao_outra": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "localizacao_outra": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "doente_estava": forms.Select(
                attrs={"class": "form-select"}
            ),
            "atividade_no_momento": forms.Select(
                attrs={"class": "form-select"}
            ),
            "atividade_outra": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "fator_contribuinte_outro": (
                forms.TextInput(
                    attrs={"class": "form-control"}
                )
            ),
            "grades_laterais": forms.Select(
                attrs={"class": "form-select"}
            ),
            "dispositivo_auxilio": forms.Select(
                attrs={"class": "form-select"}
            ),
            "dispositivo_auxilio_outro": (
                forms.TextInput(
                    attrs={"class": "form-control"}
                )
            ),
            "morse_aplicada": forms.Select(
                attrs={"class": "form-select"}
            ),
            "score_morse_previo": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                    "max": 125,
                }
            ),
            "medidas_preventivas_implementadas": (
                forms.Select(
                    attrs={"class": "form-select"}
                )
            ),
            "intervencao_outra": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "medico_notificado": forms.Select(
                attrs={"class": "form-select"}
            ),
            "medico_notificado_em": (
                forms.DateTimeInput(
                    format="%Y-%m-%dT%H:%M",
                    attrs={
                        "class": "form-control",
                        "type": "datetime-local",
                    },
                )
            ),
            "medico_nao_notificado_justificacao": (
                forms.Textarea(
                    attrs={
                        "class": "form-control",
                        "rows": 2,
                    }
                )
            ),
            "familiar_notificado": forms.Select(
                attrs={"class": "form-select"}
            ),
            "familiar_notificado_em": (
                forms.DateTimeInput(
                    format="%Y-%m-%dT%H:%M",
                    attrs={
                        "class": "form-control",
                        "type": "datetime-local",
                    },
                )
            ),
            "descricao_ocorrencia": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 6,
                }
            ),
            "reavaliacao_morse_estado": (
                forms.Select(
                    attrs={"class": "form-select"}
                )
            ),
            "score_morse_pos": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                    "max": 125,
                }
            ),
            "medida_corretiva_outra": (
                forms.TextInput(
                    attrs={"class": "form-control"}
                )
            ),
            "observacoes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                }
            ),
            "notificacao_institucional_estado": (
                forms.Select(
                    attrs={"class": "form-select"}
                )
            ),
            "data_notificacao_institucional": (
                forms.DateInput(
                    format="%Y-%m-%d",
                    attrs={
                        "class": "form-control",
                        "type": "date",
                    },
                )
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        campos_obrigatorios = [
            "data_hora_queda",
            "local_queda",
            "tipo_queda",
            "gravidade",
            "doente_estava",
            "atividade_no_momento",
            "grades_laterais",
            "dispositivo_auxilio",
            "morse_aplicada",
            "medidas_preventivas_implementadas",
            "medico_notificado",
            "familiar_notificado",
            "descricao_ocorrencia",
            "reavaliacao_morse_estado",
            "notificacao_institucional_estado",
        ]

        for campo in campos_obrigatorios:
            self.fields[campo].required = True

        if not self.is_bound and not self.instance.pk:
            agora = timezone.localtime().replace(
                second=0,
                microsecond=0,
            )

            self.fields[
                "data_hora_queda"
            ].initial = agora

            self.fields[
                "lesoes_identificadas"
            ].initial = [
                LesaoIdentificada.NENHUMA
            ]

            self.fields[
                "gravidade"
            ].initial = GravidadeQueda.SEM_LESAO

            self.fields[
                "notificacao_institucional_estado"
            ].initial = (
                EstadoNotificacaoInstitucional.PENDENTE
            )
