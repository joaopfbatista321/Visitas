from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q

from visitas.models import Utente

from .models import (
    EstadoParticipacaoFisioterapia,
    EstadoSessaoFisioterapia,
    LocalSessaoFisioterapia,
    ParticipacaoFisioterapia,
    RegistoFisioterapia,
    SessaoFisioterapia,
    TipoIntervencaoFisioterapia,
    TipoSessaoFisioterapia,
)


GRUPO_FISIOTERAPIA = "UCCI_Fisioterapia"

User = get_user_model()


class ProfissionalFisioterapiaChoiceField(
    forms.ModelChoiceField
):
    def label_from_instance(self, obj):
        nome = obj.get_full_name().strip()
        return nome or obj.username


class SessaoFisioterapiaForm(forms.ModelForm):
    profissional = ProfissionalFisioterapiaChoiceField(
        label="Fisioterapeuta responsável",
        queryset=User.objects.none(),
        widget=forms.Select(
            attrs={"class": "form-select"}
        ),
        help_text=(
            "Profissional que realizará a sessão e poderá "
            "editar e validar as presenças."
        ),
    )

    tipos_intervencao = forms.ModelMultipleChoiceField(
        label="Tipos de intervenção",
        queryset=TipoIntervencaoFisioterapia.objects.none(),
        widget=forms.CheckboxSelectMultiple(
            
        ),
        help_text=(
            "Pode selecionar um ou vários tipos de "
            "fisioterapia ou reabilitação."
        ),
        error_messages={
            "required": (
                "Selecione pelo menos um tipo de intervenção."
            ),
        },
    )

    utentes = forms.ModelMultipleChoiceField(
        label="Utentes",
        queryset=Utente.objects.none(),
        widget=forms.CheckboxSelectMultiple(
            
        ),
        help_text=(
            "Selecione um utente para uma sessão individual "
            "ou dois ou mais para uma sessão de grupo."
        ),
        error_messages={
            "required": "Selecione pelo menos um utente.",
        },
    )

    class Meta:
        model = SessaoFisioterapia
        fields = [
            "profissional",
            "tipo",
            "tipos_intervencao",
            "utentes",
            "inicio",
            "fim",
            "local_realizacao",
            "local",
            "trabalho_planeado",
            "observacoes",
        ]

        widgets = {
            "tipo": forms.Select(
                attrs={"class": "form-select"}
            ),
            "inicio": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                },
            ),
            "fim": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                },
            ),
            "local_realizacao": forms.Select(
                attrs={"class": "form-select"}
            ),
            "local": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "Ex.: ginásio, exterior, quarto 12..."
                    ),
                }
            ),
            "trabalho_planeado": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": (
                        "Descreva os objetivos e o trabalho "
                        "planeado para a sessão."
                    ),
                }
            ),
            "observacoes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": (
                        "Informações de organização, material "
                        "necessário ou outros cuidados."
                    ),
                }
            ),
        }

    def __init__(
        self,
        *args,
        profissional=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.utilizador_atual = profissional

        self.fields["inicio"].input_formats = [
            "%Y-%m-%dT%H:%M",
        ]
        self.fields["fim"].input_formats = [
            "%Y-%m-%dT%H:%M",
        ]

        profissionais = (
            User.objects
            .filter(
                is_active=True,
                groups__name=GRUPO_FISIOTERAPIA,
            )
            .distinct()
            .order_by(
                "first_name",
                "last_name",
                "username",
            )
        )

        self.fields["profissional"].queryset = profissionais

        if (
            not self.is_bound
            and not self.instance.pk
            and profissional
            and profissionais.filter(
                pk=profissional.pk
            ).exists()
        ):
            self.fields["profissional"].initial = profissional

        tipos_intervencao = (
            TipoIntervencaoFisioterapia.objects
            .filter(ativo=True)
        )

        if self.instance and self.instance.pk:
            tipos_intervencao = (
                TipoIntervencaoFisioterapia.objects
                .filter(
                    Q(ativo=True)
                    | Q(sessoes=self.instance)
                )
                .distinct()
            )

        self.fields[
            "tipos_intervencao"
        ].queryset = tipos_intervencao.order_by(
            "ordem",
            "categoria",
            "nome",
        )

        utentes = Utente.objects.filter(
            data_saida__isnull=True
        )

        if self.instance and self.instance.pk:
            utentes = (
                Utente.objects
                .filter(
                    Q(data_saida__isnull=True)
                    | Q(
                        participacoes_fisioterapia__sessao=(
                            self.instance
                        )
                    )
                )
                .distinct()
            )

            self.fields["utentes"].initial = (
                self.instance.participacoes
                .exclude(
                    estado__in=[
                        EstadoParticipacaoFisioterapia.CANCELADO,
                        EstadoParticipacaoFisioterapia.CANCELADO_ALTA,
                    ]
                )
                .values_list(
                    "utente_id",
                    flat=True,
                )
            )

        self.fields["utentes"].queryset = (
            utentes.order_by("nome")
        )

        self.order_fields([
            "profissional",
            "tipo",
            "tipos_intervencao",
            "utentes",
            "inicio",
            "fim",
            "local_realizacao",
            "local",
            "trabalho_planeado",
            "observacoes",
        ])

    def clean(self):
        cleaned_data = super().clean()

        profissional = cleaned_data.get("profissional")
        tipo = cleaned_data.get("tipo")
        tipos_intervencao = cleaned_data.get(
            "tipos_intervencao"
        )
        utentes = cleaned_data.get("utentes")
        inicio = cleaned_data.get("inicio")
        fim = cleaned_data.get("fim")
        local_realizacao = cleaned_data.get(
            "local_realizacao"
        )
        local = cleaned_data.get("local", "").strip()

        if not tipos_intervencao:
            self.add_error(
                "tipos_intervencao",
                (
                    "Selecione pelo menos um tipo "
                    "de intervenção."
                ),
            )

        if (
            local_realizacao
            == LocalSessaoFisioterapia.OUTRO
            and not local
        ):
            self.add_error(
                "local",
                "Indique onde será realizada a sessão.",
            )

        if not utentes:
            return cleaned_data

        quantidade = utentes.count()

        if (
            tipo == TipoSessaoFisioterapia.INDIVIDUAL
            and quantidade != 1
        ):
            self.add_error(
                "utentes",
                (
                    "Uma sessão individual deve ter "
                    "exatamente um utente."
                ),
            )

        if (
            tipo == TipoSessaoFisioterapia.GRUPO
            and quantidade < 2
        ):
            self.add_error(
                "utentes",
                (
                    "Uma sessão de grupo deve ter "
                    "pelo menos dois utentes."
                ),
            )

        utentes_com_alta = [
            utente.nome
            for utente in utentes
            if utente.data_saida
        ]

        if utentes_com_alta:
            self.add_error(
                "utentes",
                (
                    "Não é possível marcar utentes com alta: "
                    + ", ".join(utentes_com_alta)
                ),
            )

        if not inicio or not fim or fim <= inicio:
            return cleaned_data

        sessoes_sobrepostas = (
            SessaoFisioterapia.objects
            .exclude(
                estado=EstadoSessaoFisioterapia.CANCELADA
            )
            .filter(
                inicio__lt=fim,
                fim__gt=inicio,
            )
        )

        if self.instance and self.instance.pk:
            sessoes_sobrepostas = (
                sessoes_sobrepostas.exclude(
                    pk=self.instance.pk
                )
            )

        if (
            profissional
            and sessoes_sobrepostas.filter(
                profissional=profissional
            ).exists()
        ):
            self.add_error(
                "inicio",
                (
                    "O fisioterapeuta selecionado já possui "
                    "outra sessão marcada neste horário."
                ),
            )

        conflitos = (
            ParticipacaoFisioterapia.objects
            .filter(
                sessao__in=sessoes_sobrepostas,
                utente__in=utentes,
            )
            .exclude(
                estado__in=[
                    EstadoParticipacaoFisioterapia.CANCELADO,
                    EstadoParticipacaoFisioterapia.CANCELADO_ALTA,
                ]
            )
            .select_related("utente")
        )

        nomes_conflito = sorted({
            participacao.utente.nome
            for participacao in conflitos
        })

        if nomes_conflito:
            self.add_error(
                "utentes",
                (
                    "Já existem marcações neste horário para: "
                    + ", ".join(nomes_conflito)
                ),
            )

        return cleaned_data


class RegistoFisioterapiaForm(forms.ModelForm):
    tipos_intervencao = forms.ModelMultipleChoiceField(
        label="Intervenções realizadas",
        queryset=TipoIntervencaoFisioterapia.objects.none(),
        widget=forms.CheckboxSelectMultiple(
            
        ),
        help_text=(
            "Selecione todas as intervenções realizadas "
            "durante o atendimento."
        ),
        error_messages={
            "required": (
                "Selecione pelo menos uma intervenção realizada."
            ),
        },
    )

    class Meta:
        model = RegistoFisioterapia
        fields = [
            "data_registo",
            "tipos_intervencao",
            "tipo_trabalho",
            "trabalho_realizado",
            "resposta_utente",
            "plano_seguinte",
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
            "tipo_trabalho": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "Descrição adicional opcional"
                    ),
                }
            ),
            "trabalho_realizado": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": (
                        "Descreva o trabalho efetuado."
                    ),
                }
            ),
            "resposta_utente": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": (
                        "Registe a resposta e evolução do utente."
                    ),
                }
            ),
            "plano_seguinte": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": (
                        "Indique o plano para a próxima sessão."
                    ),
                }
            ),
            "visibilidade": forms.Select(
                attrs={"class": "form-select"}
            ),
        }

    def __init__(
        self,
        *args,
        participacao=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.fields["data_registo"].input_formats = [
            "%Y-%m-%dT%H:%M",
        ]

        tipos_intervencao = (
            TipoIntervencaoFisioterapia.objects
            .filter(ativo=True)
        )

        if self.instance and self.instance.pk:
            tipos_intervencao = (
                TipoIntervencaoFisioterapia.objects
                .filter(
                    Q(ativo=True)
                    | Q(registos=self.instance)
                )
                .distinct()
            )

        self.fields[
            "tipos_intervencao"
        ].queryset = tipos_intervencao.order_by(
            "ordem",
            "categoria",
            "nome",
        )

        if (
            not self.is_bound
            and not self.instance.pk
            and participacao
        ):
            self.fields[
                "tipos_intervencao"
            ].initial = (
                participacao.sessao
                .tipos_intervencao
                .values_list("pk", flat=True)
            )

        self.order_fields([
            "data_registo",
            "tipos_intervencao",
            "tipo_trabalho",
            "trabalho_realizado",
            "resposta_utente",
            "plano_seguinte",
            "visibilidade",
        ])