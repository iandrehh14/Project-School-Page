from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class IdentificadorBackend(ModelBackend):
    """
    Permite iniciar sesión con nombre de usuario, correo o documento.
    Hereda de ModelBackend, así que permisos y grupos siguen funcionando.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        Usuario = get_user_model()
        identificador = username.strip()

        try:
            usuario = Usuario.objects.get(
                Q(username__iexact=identificador)
                | Q(email__iexact=identificador)
                | Q(documento=identificador)
            )
        except Usuario.DoesNotExist:
            # Cifra igualmente para que no se note si la cuenta existe o no
            Usuario().set_password(password)
            return None
        except Usuario.MultipleObjectsReturned:
            return None

        if usuario.check_password(password) and self.user_can_authenticate(usuario):
            return usuario
        return None