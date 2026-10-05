from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


# ----------------------------------------------------------------------
#  Grupos y asignaturas
# ----------------------------------------------------------------------

class Grupo(models.Model):
    """Un curso del colegio, por ejemplo «10-A»."""

    nombre = models.CharField("nombre", max_length=20, unique=True, help_text="Ejemplo: 10-A")

    class Meta:
        verbose_name = "grupo"
        verbose_name_plural = "grupos"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Asignatura(models.Model):
    nombre = models.CharField("nombre", max_length=60, unique=True)

    class Meta:
        verbose_name = "asignatura"
        verbose_name_plural = "asignaturas"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


# ----------------------------------------------------------------------
#  Visibilidad: qué ve cada usuario
# ----------------------------------------------------------------------

class VisibilidadQuerySet(models.QuerySet):
    """
    Filtra avisos y comunicados según quién los mira.

    - Sin grupos asignados  -> lo ve todo el colegio.
    - Con grupos asignados  -> lo ven los estudiantes de esos grupos y
      los profesores que dictan clase en alguno de ellos.
    - Administrativos y superusuarios ven todo.
    """

    def para(self, usuario):
        if usuario.is_superuser or usuario.rol == Usuario.Rol.ADMINISTRATIVO:
            return self

        if usuario.rol == Usuario.Rol.PROFESOR:
            grupos = Grupo.objects.filter(clases__profesor=usuario).values("pk")
        else:
            grupos = [usuario.grupo_id] if usuario.grupo_id else []

        return self.filter(Q(grupos__isnull=True) | Q(grupos__in=grupos)).distinct()


class AvisoQuerySet(VisibilidadQuerySet):
    def vigentes(self):
        hoy = timezone.localdate()
        return self.filter(activo=True, visible_desde__lte=hoy).filter(
            Q(visible_hasta__isnull=True) | Q(visible_hasta__gte=hoy)
        )


class ConDestinatarios(models.Model):
    """Base común: algo que puede ir a todo el colegio o a grupos concretos."""

    grupos = models.ManyToManyField(
        Grupo,
        blank=True,
        verbose_name="grupos destinatarios",
        help_text="Déjelo vacío para que lo vea todo el colegio.",
    )

    objects = VisibilidadQuerySet.as_manager()

    class Meta:
        abstract = True

    @property
    def destinatarios(self):
        nombres = [g.nombre for g in self.grupos.all()]
        return ", ".join(nombres) if nombres else "Todo el colegio"


# ----------------------------------------------------------------------
#  Usuario
# ----------------------------------------------------------------------

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
    grupo = models.ForeignKey(
        Grupo,
        verbose_name="grupo",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="estudiantes",
        help_text="Solo para estudiantes.",
    )

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
        if self.grupo_id and self.rol != self.Rol.ESTUDIANTE:
            raise ValidationError({"grupo": "Solo los estudiantes pertenecen a un grupo."})

    def save(self, *args, **kwargs):
        self.username = self.username.strip().lower()
        self.email = self.email.strip().lower()
        self.documento = self.documento.strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.get_full_name() or self.username


# ----------------------------------------------------------------------
#  Horario
# ----------------------------------------------------------------------

class ClaseHorario(models.Model):
    """Una clase que se repite todas las semanas."""

    class Dia(models.IntegerChoices):
        # Los números coinciden con date.weekday() de Python
        LUNES = 0, "Lunes"
        MARTES = 1, "Martes"
        MIERCOLES = 2, "Miércoles"
        JUEVES = 3, "Jueves"
        VIERNES = 4, "Viernes"

    grupo = models.ForeignKey(Grupo, verbose_name="grupo", on_delete=models.CASCADE, related_name="clases")
    asignatura = models.ForeignKey(Asignatura, verbose_name="asignatura", on_delete=models.PROTECT)
    profesor = models.ForeignKey(
        Usuario,
        verbose_name="profesor",
        on_delete=models.PROTECT,
        related_name="clases",
        limit_choices_to={"rol": Usuario.Rol.PROFESOR},
    )
    dia = models.IntegerField("día", choices=Dia.choices)
    hora_inicio = models.TimeField("hora de inicio")
    hora_fin = models.TimeField("hora de fin")
    salon = models.CharField("salón", max_length=30, blank=True)

    class Meta:
        verbose_name = "clase del horario"
        verbose_name_plural = "clases del horario"
        ordering = ["dia", "hora_inicio"]

    def clean(self):
        super().clean()
        if not (self.hora_inicio and self.hora_fin):
            return
        if self.hora_fin <= self.hora_inicio:
            raise ValidationError({"hora_fin": "La hora de fin debe ser posterior a la de inicio."})
        if self.dia is None:
            return

        # Cruces: mismo día y franjas que se solapan
        cruces = ClaseHorario.objects.filter(
            dia=self.dia,
            hora_inicio__lt=self.hora_fin,
            hora_fin__gt=self.hora_inicio,
        ).exclude(pk=self.pk)

        if self.grupo_id and cruces.filter(grupo_id=self.grupo_id).exists():
            raise ValidationError("Ese grupo ya tiene una clase en esa franja horaria.")
        if self.profesor_id and cruces.filter(profesor_id=self.profesor_id).exists():
            raise ValidationError("Ese profesor ya tiene una clase en esa franja horaria.")

    def __str__(self):
        return f"{self.grupo} · {self.get_dia_display()} {self.hora_inicio:%H:%M} · {self.asignatura}"


# ----------------------------------------------------------------------
#  Avisos y comunicados
# ----------------------------------------------------------------------

class Aviso(ConDestinatarios):
    """Aviso corto con fechas de vigencia: caduca solo."""

    texto = models.CharField("texto", max_length=250)
    visible_desde = models.DateField("visible desde", default=timezone.localdate)
    visible_hasta = models.DateField("visible hasta", null=True, blank=True, help_text="Opcional. Vacío = sin fecha de fin.")
    activo = models.BooleanField("activo", default=True)

    objects = AvisoQuerySet.as_manager()

    class Meta:
        verbose_name = "aviso"
        verbose_name_plural = "avisos"
        ordering = ["-visible_desde", "-id"]

    def clean(self):
        super().clean()
        if self.visible_hasta and self.visible_desde and self.visible_hasta < self.visible_desde:
            raise ValidationError({"visible_hasta": "No puede ser anterior a la fecha de inicio."})

    def __str__(self):
        return self.texto[:60]


class Comunicado(ConDestinatarios):
    class Tipo(models.TextChoices):
        COMUNICADO = "comunicado", "Comunicado"
        TAREA = "tarea", "Tarea"
        EVENTO = "evento", "Evento"

    autor = models.ForeignKey(
        Usuario,
        verbose_name="autor",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="comunicados",
    )
    tipo = models.CharField("tipo", max_length=20, choices=Tipo.choices, default=Tipo.COMUNICADO)
    titulo = models.CharField("título", max_length=150)
    contenido = models.TextField("contenido")
    publicado = models.DateTimeField("publicado", default=timezone.now)
    activo = models.BooleanField("activo", default=True)

    class Meta:
        verbose_name = "comunicado"
        verbose_name_plural = "comunicados"
        ordering = ["-publicado"]

    def __str__(self):
        return self.titulo