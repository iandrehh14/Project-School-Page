from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, URLValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone
import os, uuid
from datetime import timedelta
from django.core.validators import FileExtensionValidator

# Los enlaces de Teams deben ser https (esto además bloquea «javascript:» y similares)
validar_https = URLValidator(schemes=["https"])


def formato_hora(hora):
    """7:00am, 12:30pm, 1:15pm (sin depender del idioma del sistema)."""
    return f"{hora.hour % 12 or 12}:{hora.minute:02d}{'am' if hora.hour < 12 else 'pm'}"


# ----------------------------------------------------------------------
#  Grupos y asignaturas
# ----------------------------------------------------------------------

class Grupo(models.Model):
    """Un grado o curso del colegio, por ejemplo «11°» o «4°A»."""

    nombre = models.CharField("nombre", max_length=20, unique=True, help_text="Ejemplo: 11°  o  4°A")
    orden = models.PositiveSmallIntegerField(
        "orden",
        default=0,
        help_text="Posición en la cuadrícula de la página de horarios (1 va primero).",
    )
    director = models.ForeignKey(
        "Usuario",
        verbose_name="director de grupo",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="grupos_dirigidos",
        limit_choices_to={"rol": "profesor"},
    )

    class Meta:
        verbose_name = "grupo"
        verbose_name_plural = "grupos"
        ordering = ["orden", "nombre"]

    def __str__(self):
        return self.nombre

    ciclo = models.ForeignKey(
        "Ciclo", verbose_name="ciclo de la biblioteca", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="grupos",
    )


class Asignatura(models.Model):
    class Icono(models.TextChoices):
        TECNOLOGIA = "tecnologia", "Tecnología (monitor)"
        EDUCACION_FISICA = "educacion_fisica", "Educación física (persona)"
        ARTISTICA = "artistica", "Artística (paleta)"
        ETICA = "etica", "Ética (balanza)"
        RELIGION = "religion", "Religión (cruz)"
        LENGUA = "lengua", "Lengua castellana (libro)"
        SOCIALES = "sociales", "Sociales (globo)"
        MATEMATICAS = "matematicas", "Matemáticas (calculadora)"
        BIOLOGIA = "biologia", "Biología (microscopio)"
        QUIMICA = "quimica", "Química (matraz)"
        FISICA = "fisica", "Física (átomo)"
        FILOSOFIA = "filosofia", "Filosofía (interrogación)"
        INGLES = "ingles", "Inglés (globo de diálogo)"
        GENERAL = "general", "General (portátil)"

    nombre = models.CharField("nombre", max_length=60, unique=True)
    nombre_corto = models.CharField(
        "nombre corto",
        max_length=30,
        blank=True,
        default="",
        help_text="Opcional. Se muestra bajo el ícono de Teams. Si está vacío se usa el nombre completo.",
    )
    icono = models.CharField("ícono", max_length=20, choices=Icono.choices, default=Icono.GENERAL)
    es_materia = models.BooleanField(
        "es una materia",
        default=True,
        help_text="Desmárquelo para entradas como «Trabajo autónomo» o «Dir. de grupo»: "
                  "salen en la tabla del horario, pero no llevan profesor ni aparecen en «Horario de hoy».",
    )

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

class Franja(models.Model):
    """
    Una fila de la jornada (7:00 - 7:45, descanso 9:15 - 9:35...).
    Es la misma para todos los grupos.
    """

    orden = models.PositiveSmallIntegerField("orden", unique=True, help_text="1 es la primera franja del día.")
    hora_inicio = models.TimeField("hora de inicio")
    hora_fin = models.TimeField("hora de fin")
    es_descanso = models.BooleanField("es un descanso", default=False)

    class Meta:
        verbose_name = "franja de la jornada"
        verbose_name_plural = "franjas de la jornada"
        ordering = ["orden"]

    @property
    def etiqueta(self):
        return f"{formato_hora(self.hora_inicio)} - {formato_hora(self.hora_fin)}"

    def clean(self):
        super().clean()
        if not (self.hora_inicio and self.hora_fin):
            return
        if self.hora_fin <= self.hora_inicio:
            raise ValidationError({"hora_fin": "La hora de fin debe ser posterior a la de inicio."})
        cruce = Franja.objects.filter(
            hora_inicio__lt=self.hora_fin, hora_fin__gt=self.hora_inicio
        ).exclude(pk=self.pk)
        if cruce.exists():
            raise ValidationError("Esa franja se cruza con otra ya registrada.")

    def __str__(self):
        return f"{self.orden}. {self.etiqueta}" + (" (descanso)" if self.es_descanso else "")


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
    dia = models.IntegerField("día", choices=Dia.choices)
    franja = models.ForeignKey(
        Franja,
        verbose_name="franja",
        null=True,
        on_delete=models.PROTECT,
        related_name="clases",
        limit_choices_to={"es_descanso": False},
    )
    asignatura = models.ForeignKey(Asignatura, verbose_name="asignatura", on_delete=models.PROTECT)
    profesor = models.ForeignKey(
        Usuario,
        verbose_name="profesor",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="clases",
        limit_choices_to={"rol": Usuario.Rol.PROFESOR},
        help_text="Obligatorio para materias. Se deja vacío en «Trabajo autónomo» y «Dir. de grupo».",
    )
    salon = models.CharField("salón", max_length=30, blank=True)

    # Se copian solos desde la franja (por eso no se editan a mano)
    hora_inicio = models.TimeField("hora de inicio", editable=False)
    hora_fin = models.TimeField("hora de fin", editable=False)

    class Meta:
        verbose_name = "clase del horario"
        verbose_name_plural = "clases del horario"
        ordering = ["dia", "hora_inicio"]
        constraints = [
            models.UniqueConstraint(
                fields=["grupo", "dia", "franja"],
                name="unica_clase_por_grupo_y_franja",
                violation_error_message="Ese grupo ya tiene una clase en esa franja.",
            ),
            models.UniqueConstraint(
                fields=["profesor", "dia", "franja"],
                name="unica_clase_por_profesor_y_franja",
                violation_error_message="Ese profesor ya tiene una clase en esa franja.",
            ),
        ]

    def _copiar_horas_de_la_franja(self):
        if self.franja_id:
            self.hora_inicio = self.franja.hora_inicio
            self.hora_fin = self.franja.hora_fin

    def clean(self):
        super().clean()
        if self.franja_id and self.franja.es_descanso:
            raise ValidationError({"franja": "No se puede poner una clase en un descanso."})
        if self.asignatura_id and self.asignatura.es_materia and not self.profesor_id:
            raise ValidationError({"profesor": "Las materias necesitan un profesor."})
        self._copiar_horas_de_la_franja()

    def save(self, *args, **kwargs):
        self._copiar_horas_de_la_franja()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.grupo} · {self.get_dia_display()} {self.hora_inicio:%H:%M} · {self.asignatura}"


class EnlaceMateria(models.Model):
    """Enlace a la clase de Teams de una materia en un grupo."""

    grupo = models.ForeignKey(Grupo, verbose_name="grupo", on_delete=models.CASCADE, related_name="enlaces")
    asignatura = models.ForeignKey(Asignatura, verbose_name="asignatura", on_delete=models.CASCADE)
    url = models.URLField("enlace de Teams", max_length=600, validators=[validar_https])
    orden = models.PositiveSmallIntegerField("orden", default=0, help_text="Orden de los íconos en la ventana.")

    class Meta:
        verbose_name = "enlace de Teams de una materia"
        verbose_name_plural = "enlaces de Teams de las materias"
        ordering = ["orden", "asignatura__nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["grupo", "asignatura"],
                name="unico_enlace_por_grupo_y_asignatura",
                violation_error_message="Ese grupo ya tiene un enlace para esa asignatura.",
            ),
        ]

    def __str__(self):
        return f"{self.grupo} · {self.asignatura}"


class Espacio(models.Model):
    """Lugar con enlace propio en la página de horarios, como el Auditorio."""

    nombre = models.CharField("nombre", max_length=40, unique=True)
    url = models.URLField("enlace", max_length=600, validators=[validar_https])
    orden = models.PositiveSmallIntegerField("orden", default=0)

    class Meta:
        verbose_name = "espacio"
        verbose_name_plural = "espacios"
        ordering = ["orden", "nombre"]

    def __str__(self):
        return self.nombre


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

    # ---------------------------------------------------------------
# PEGAR AL FINAL de Main/models.py  (no borra ni cambia nada existente)
# ---------------------------------------------------------------

class Ciclo(models.Model):
    """Ciclo académico de la biblioteca (Inicial, Primaria avanzada, etc.)."""

    nombre = models.CharField("nombre", max_length=60, unique=True)
    grados = models.CharField("grados", max_length=40, blank=True, help_text='Ej.: "Grado 1° - 3°"')
    descripcion = models.CharField("descripción", max_length=160, blank=True)
    es_transversal = models.BooleanField(
        "es el ciclo central (transversal)",
        default=False,
        help_text="Se muestra en el centro de la biblioteca. Solo debería haber uno.",
    )
    orden = models.PositiveSmallIntegerField("orden", default=0)

    class Meta:
        ordering = ["orden", "nombre"]
        verbose_name = "ciclo"
        verbose_name_plural = "ciclos"

    def __str__(self):
        return self.nombre


class AreaBiblioteca(models.Model):
    """Área (materia agrupada) dentro de un ciclo. Cada ciclo tiene las suyas."""

    ciclo = models.ForeignKey(Ciclo, on_delete=models.CASCADE, related_name="areas", verbose_name="ciclo")
    nombre = models.CharField("nombre", max_length=60)
    detalle = models.CharField("detalle", max_length=60, blank=True, help_text='Ej.: "Castellano · Inglés"')
    icono = models.CharField(
        "ícono", max_length=20, choices=Asignatura.Icono.choices, default=Asignatura.Icono.GENERAL
    )
    orden = models.PositiveSmallIntegerField("orden", default=0)

    class Meta:
        ordering = ["ciclo__orden", "orden", "nombre"]
        verbose_name = "área de la biblioteca"
        verbose_name_plural = "áreas de la biblioteca"
        constraints = [
            models.UniqueConstraint(
                fields=["ciclo", "nombre"],
                name="area_unica_por_ciclo",
                violation_error_message="Ese ciclo ya tiene un área con ese nombre.",
            )
        ]

    def __str__(self):
        return f"{self.nombre} ({self.ciclo})"



MAX_MB = 25                      # tamaño máximo por archivo
MAX_BYTES = MAX_MB * 1024 * 1024
EXTENSIONES = ["pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "jpg", "jpeg", "png", "zip", "mp4"]


def ruta_material(instancia, nombre):
    """Guarda con un nombre aleatorio: no se pisan archivos ni se adivinan direcciones."""
    extension = os.path.splitext(nombre)[1].lower()
    return f"materiales/{timezone.localdate():%Y/%m}/{uuid.uuid4().hex}{extension}"


class MaterialQuerySet(models.QuerySet):
    def para(self, usuario):
        """Lo que puede ver cada persona (estudiante, profesor o administrativo)."""
        if usuario.is_superuser or usuario.rol == Usuario.Rol.ADMINISTRATIVO:
            return self

        if usuario.rol == Usuario.Rol.PROFESOR:
            grupos = Grupo.objects.filter(clases__profesor=usuario)
            return self.filter(
                Q(profesor=usuario)
                | Q(grupos__in=grupos)
                | Q(todo_ciclo=True, area__ciclo__in=grupos.values("ciclo"))
                | Q(area__ciclo__es_transversal=True)
            ).distinct()

        condicion = Q(area__ciclo__es_transversal=True)
        if usuario.grupo_id:
            condicion |= Q(grupos=usuario.grupo_id)
            condicion |= Q(todo_ciclo=True, area__ciclo=usuario.grupo.ciclo_id)
        return self.filter(condicion).distinct()


class Material(models.Model):
    """Archivo o enlace que un profesor publica en la biblioteca."""

    class Tipo(models.TextChoices):
        GUIA = "guia", "Guía"
        TALLER = "taller", "Taller"
        LECTURA = "lectura", "Lectura"
        PRESENTACION = "presentacion", "Presentación"
        EVALUACION = "evaluacion", "Evaluación"
        VIDEO = "video", "Video"
        OTRO = "otro", "Otro"

    titulo = models.CharField("título", max_length=120)
    descripcion = models.TextField("descripción", max_length=500, blank=True)
    tipo = models.CharField("tipo", max_length=15, choices=Tipo.choices, default=Tipo.GUIA)
    periodo = models.PositiveSmallIntegerField(
        "periodo", choices=[(n, f"Periodo {n}") for n in range(1, 5)], default=1
    )
    area = models.ForeignKey(AreaBiblioteca, on_delete=models.CASCADE, related_name="materiales", verbose_name="área")
    grupos = models.ManyToManyField(Grupo, blank=True, related_name="materiales", verbose_name="grupos")
    todo_ciclo = models.BooleanField("todo el ciclo", default=False, help_text="Visible para todos los grupos del ciclo.")
    profesor = models.ForeignKey(
        "Usuario", null=True, blank=True, on_delete=models.SET_NULL, related_name="materiales", verbose_name="publicado por"
    )
    archivo = models.FileField(
        "archivo", upload_to=ruta_material, blank=True,
        validators=[FileExtensionValidator(EXTENSIONES)],
    )
    nombre_archivo = models.CharField(max_length=200, blank=True, editable=False)
    tamano = models.PositiveIntegerField(default=0, editable=False)
    enlace = models.URLField("enlace", blank=True, help_text="Drive, YouTube, Teams… debe empezar con https://")
    creado = models.DateTimeField(auto_now_add=True)

    objects = MaterialQuerySet.as_manager()

    class Meta:
        ordering = ["-creado"]
        verbose_name = "material"
        verbose_name_plural = "materiales"

    def __str__(self):
        return self.titulo

    def clean(self):
        super().clean()
        if self.enlace and not self.enlace.lower().startswith("https://"):
            raise ValidationError({"enlace": "El enlace debe comenzar con https://"})
        if self.archivo and not self.archivo._committed and self.archivo.size > MAX_BYTES:
            raise ValidationError(
                {"archivo": f"Este archivo pesa {self.archivo.size / 1048576:.1f} MB; el máximo es {MAX_MB} MB."}
            )
        if self.archivo and self.enlace:
            raise ValidationError("Elija un archivo o un enlace, no ambos.")
        if not self.archivo and not self.enlace:
            raise ValidationError("Suba un archivo o pegue un enlace.")

    def save(self, *args, **kwargs):
        previo = Material.objects.filter(pk=self.pk).first() if self.pk else None
        if self.archivo and not self.archivo._committed:
            self.nombre_archivo = os.path.basename(self.archivo.name)[:200]
            self.tamano = self.archivo.size
        elif not self.archivo:
            self.nombre_archivo, self.tamano = "", 0
        super().save(*args, **kwargs)
        if previo and previo.archivo and previo.archivo.name != self.archivo.name:
            previo.archivo.delete(save=False)  # no deja archivos huérfanos al reemplazar

    def delete(self, *args, **kwargs):
        if self.archivo:
            self.archivo.delete(save=False)
        return super().delete(*args, **kwargs)

    @property
    def es_enlace(self):
        return not self.archivo

    @property
    def etiqueta_formato(self):
        if self.es_enlace:
            return "ENLACE"
        return os.path.splitext(self.nombre_archivo)[1].lstrip(".").upper()[:4] or "ARCHIVO"

    @property
    def es_nuevo(self):
        return timezone.now() - self.creado <= timedelta(days=7)