from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models


class Usuario(AbstractUser):
    """
    Cuenta de acceso al sitio. Solo el colegio las crea (desde /admin).

    Se puede iniciar sesión con cualquiera de los tres identificadores:
    nombre de usuario, correo o documento. Para que nunca se confundan:
      - el documento son solo números,
      - el correo siempre lleva "@",
      - el nombre de usuario no puede ser solo números ni llevar "@".
    """

    class Rol(models.TextChoices):
        ESTUDIANTE = "estudiante", "Estudiante"
        PROFESOR = "profesor", "Profesor"
        ADMINISTRATIVO = "administrativo", "Administrativo"

    documento = models.CharField(
        "documento",
        max_length=15,
        unique=True,
        validators=[RegexValidator(r"^\d{5,15}$", "Solo números, entre 5 y 15 dígitos.")],
    )
    email = models.EmailField("correo electrónico", unique=True)
    rol = models.CharField("rol", max_length=20, choices=Rol.choices, default=Rol.ESTUDIANTE)

    # Lo que pregunta "createsuperuser" además del usuario y la contraseña
    REQUIRED_FIELDS = ["documento", "email"]

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"

    def clean(self):
        super().clean()
        # Usuario y correo siempre en minúsculas: evita duplicados como "Juan" y "juan"
        self.username = (self.username or "").strip().lower()
        self.email = (self.email or "").strip().lower()

        if self.username.isdigit():
            raise ValidationError(
                {"username": "El nombre de usuario no puede ser solo números (se confundiría con un documento)."}
            )
        if "@" in self.username:
            raise ValidationError(
                {"username": "El nombre de usuario no puede llevar «@» (se confundiría con un correo)."}
            )

    def save(self, *args, **kwargs):
        self.username = self.username.strip().lower()
        self.email = self.email.strip().lower()
        self.documento = self.documento.strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.get_full_name() or self.username