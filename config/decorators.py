from functools import wraps

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied


def grupos_permitidos(*nomes_grupos):
    """
    Permite o acesso ao superutilizador ou a quem pertença
    a pelo menos um dos grupos indicados.
    """

    def decorador(view_function):
        @wraps(view_function)
        def wrapper(request, *args, **kwargs):
            utilizador = request.user

            if not utilizador.is_authenticated:
                return redirect_to_login(
                    request.get_full_path(),
                    settings.LOGIN_URL,
                )

            if utilizador.is_superuser:
                return view_function(request, *args, **kwargs)

            autorizado = utilizador.groups.filter(
                name__in=nomes_grupos
            ).exists()

            if not autorizado:
                raise PermissionDenied(
                    "Não tem autorização para aceder a esta área."
                )

            return view_function(request, *args, **kwargs)

        return wrapper

    return decorador