from django.contrib.auth import views as auth_views
from django.contrib.auth.forms import PasswordChangeForm
from django.urls import path, reverse_lazy


class FormularioAlterarPalavraPasse(PasswordChangeForm):
    """Formulário de alteração da palavra-passe com apresentação Datta Able."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        configuracao = {
            "old_password": {
                "label": "Palavra-passe atual",
                "placeholder": "Introduza a palavra-passe atual",
                "autocomplete": "current-password",
            },
            "new_password1": {
                "label": "Nova palavra-passe",
                "placeholder": "Introduza a nova palavra-passe",
                "autocomplete": "new-password",
            },
            "new_password2": {
                "label": "Confirmar nova palavra-passe",
                "placeholder": "Repita a nova palavra-passe",
                "autocomplete": "new-password",
            },
        }

        for nome, opcoes in configuracao.items():
            campo = self.fields[nome]
            campo.label = opcoes["label"]
            campo.widget.attrs.update(
                {
                    "class": "form-control",
                    "placeholder": opcoes["placeholder"],
                    "autocomplete": opcoes["autocomplete"],
                }
            )

        self.fields["new_password1"].help_text = (
            "Utilize pelo menos 8 caracteres. Evite palavras-passe comuns, "
            "apenas números ou dados pessoais."
        )
        self.fields["new_password2"].help_text = (
            "Introduza novamente a nova palavra-passe para confirmação."
        )


app_name = "conta"


urlpatterns = [
    path(
        "conta/alterar-palavra-passe/",
        auth_views.PasswordChangeView.as_view(
            template_name="accounts/password_change.html",
            form_class=FormularioAlterarPalavraPasse,
            success_url=reverse_lazy(
                "conta:alterar_password_concluida"
            ),
        ),
        name="alterar_password",
    ),
    path(
        "conta/alterar-palavra-passe/concluida/",
        auth_views.PasswordChangeDoneView.as_view(
            template_name="accounts/password_change_done.html",
        ),
        name="alterar_password_concluida",
    ),
]
