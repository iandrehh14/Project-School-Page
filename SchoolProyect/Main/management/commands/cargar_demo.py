from datetime import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from Main.models import (
    Asignatura, Aviso, ClaseHorario, Comunicado, EnlaceMateria, Espacio, Franja, Grupo, Usuario,
)

CLAVE = "Colegio2026!"

# Enlace de relleno: el colegio debe reemplazarlo por los reales desde /admin
ENLACE_DEMO = "https://teams.microsoft.com/"

GRADOS = ["1°", "2°", "3°", "4°A", "4°B", "5°", "6°7", "6°8", "7°7", "7°8", "8°", "9°", "10°", "11°"]

# (orden, inicio, fin, es_descanso): la jornada es la misma para todos los grupos
FRANJAS = [
    (1, time(7, 0), time(7, 45), False),
    (2, time(7, 45), time(8, 30), False),
    (3, time(8, 30), time(9, 15), False),
    (4, time(9, 15), time(9, 35), True),
    (5, time(9, 35), time(10, 20), False),
    (6, time(10, 20), time(11, 5), False),
    (7, time(11, 5), time(11, 50), False),
    (8, time(11, 50), time(12, 30), True),
    (9, time(12, 30), time(13, 15), False),
]

# nombre: (nombre corto, ícono, es materia, usuario del profesor)
ASIGNATURAS = {
    "Matemáticas": ("", "matematicas", True, "prof.daniel"),
    "Física": ("", "fisica", True, "prof.sara"),
    "Inglés": ("", "ingles", True, "prof.laura"),
    "Tecnología": ("", "tecnologia", True, "prof.diego"),
    "Filosofía": ("", "filosofia", True, "prof.laura"),
    "Ed. Física": ("", "educacion_fisica", True, "prof.jennifer"),
    "Artística": ("", "artistica", True, "prof.carlos"),
    "Lengua Castellana": ("L. Castellana", "lengua", True, "prof.laura"),
    "Química": ("", "quimica", True, "prof.mariana"),
    "C. Sociales": ("", "sociales", True, "prof.yeison"),
    "Biología": ("", "biologia", True, "prof.sara"),
    "C. Políticas": ("", "general", True, "prof.yeison"),
    "Ética": ("", "etica", True, "prof.carlos"),
    "C. Religiosas": ("Religión", "religion", True, "prof.carlos"),
    "Trabajo autónomo": ("", "general", False, None),
    "Dir. de grupo": ("", "general", False, None),
    "General": ("", "general", False, None),  # solo para el enlace general de Teams
}

# Horario de 11°: una fila por franja (por su orden), de lunes a viernes
HORARIO_11 = {
    1: ["Dir. de grupo", "Matemáticas", "Física", "Matemáticas", "Inglés"],
    2: ["Física", "Matemáticas", "Tecnología", "Filosofía", "Inglés"],
    3: ["Física", "Ed. Física", "Tecnología", "Filosofía", "Trabajo autónomo"],
    5: ["Inglés", "Artística", "Lengua Castellana", "Química", "C. Sociales"],
    6: ["Trabajo autónomo", "Química", "Lengua Castellana", "Química", "C. Sociales"],
    7: ["Biología", "Química", "C. Políticas", "Lengua Castellana", "Física"],
    9: ["Ética", "Trabajo autónomo", "Matemáticas", "Lengua Castellana", "C. Religiosas"],
}

# Orden de los íconos de Teams en la ventana de 11°
ENLACES_11 = [
    "Tecnología", "Ed. Física", "Artística", "Ética", "C. Religiosas", "Lengua Castellana",
    "C. Sociales", "Matemáticas", "Biología", "Química", "Física", "Filosofía", "Inglés", "General",
]


class Command(BaseCommand):
    help = "Carga datos de ejemplo (grados, jornada, horario de 11°, avisos y comunicados). Solo para desarrollo."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Este comando es solo para desarrollo (DEBUG debe ser True).")

        self.limpiar_demo_anterior()

        # --- Grupos ------------------------------------------------------
        grupos = {}
        for posicion, nombre in enumerate(GRADOS, start=1):
            grupo, _ = Grupo.objects.update_or_create(nombre=nombre, defaults={"orden": posicion})
            grupos[nombre] = grupo
        g11 = grupos["11°"]

        # --- Jornada -----------------------------------------------------
        franjas = {}
        for orden, inicio, fin, descanso in FRANJAS:
            franja, _ = Franja.objects.update_or_create(
                orden=orden,
                defaults={"hora_inicio": inicio, "hora_fin": fin, "es_descanso": descanso},
            )
            franjas[orden] = franja

        # --- Profesores y estudiante --------------------------------------
        def usuario(username, documento, nombre, apellido, rol, grupo=None):
            u, creado = Usuario.objects.get_or_create(
                username=username,
                defaults=dict(
                    documento=documento,
                    email=f"{username}@demo.local",
                    first_name=nombre,
                    last_name=apellido,
                    rol=rol,
                    grupo=grupo,
                ),
            )
            if creado:
                u.set_password(CLAVE)
                u.save()
            elif grupo is not None and u.grupo_id != grupo.pk:
                u.grupo = grupo
                u.save()
            return u

        P = Usuario.Rol.PROFESOR
        profes = {
            "prof.daniel": usuario("prof.daniel", "1000000011", "Daniel", "Gómez", P),
            "prof.mariana": usuario("prof.mariana", "1000000012", "Mariana", "Ríos", P),
            "prof.yeison": usuario("prof.yeison", "1000000013", "Yeison", "Castaño", P),
            "prof.jennifer": usuario("prof.jennifer", "1000000014", "Jennifer", "Mejía", P),
            "prof.diego": usuario("prof.diego", "1000000015", "Diego Andres", "Ocampo", P),
            "prof.sara": usuario("prof.sara", "1000000016", "Sara", "Echeverri", P),
            "prof.laura": usuario("prof.laura", "1000000017", "Laura", "Mesa", P),
            "prof.carlos": usuario("prof.carlos", "1000000018", "Carlos", "Pérez", P),
        }
        usuario("juan.andres", "1000000001", "Juan Andres", "Rodríguez", Usuario.Rol.ESTUDIANTE, g11)

        g11.director = profes["prof.sara"]
        g11.save()

        # --- Asignaturas --------------------------------------------------
        asignaturas = {}
        for nombre, (corto, icono, es_materia, _profe) in ASIGNATURAS.items():
            asignatura, _ = Asignatura.objects.update_or_create(
                nombre=nombre,
                defaults={"nombre_corto": corto, "icono": icono, "es_materia": es_materia},
            )
            asignaturas[nombre] = asignatura

        # --- Horario de 11° -----------------------------------------------
        for orden, fila in HORARIO_11.items():
            franja = franjas[orden]
            for dia, nombre in enumerate(fila):
                profe_username = ASIGNATURAS[nombre][3]
                ClaseHorario.objects.update_or_create(
                    grupo=g11,
                    dia=dia,
                    franja=franja,
                    defaults={
                        "asignatura": asignaturas[nombre],
                        "profesor": profes[profe_username] if profe_username else None,
                        "hora_inicio": franja.hora_inicio,
                        "hora_fin": franja.hora_fin,
                    },
                )

        # --- Enlaces de Teams (no se pisan si ya los cambió a mano) ---------
        for posicion, nombre in enumerate(ENLACES_11, start=1):
            enlace, creado = EnlaceMateria.objects.get_or_create(
                grupo=g11,
                asignatura=asignaturas[nombre],
                defaults={"url": ENLACE_DEMO, "orden": posicion},
            )
            if not creado and enlace.orden != posicion:
                enlace.orden = posicion
                enlace.save()

        Espacio.objects.get_or_create(nombre="Auditorio", defaults={"url": ENLACE_DEMO, "orden": 1})

        # --- Avisos y comunicado -------------------------------------------
        for texto in (
            "Semanas de vacaciones del 19 de junio al 14 de julio",
            "Pre Informe el próximo viernes después de vacaciones",
            "Reunión de padres el viernes 7 de junio",
        ):
            Aviso.objects.get_or_create(texto=texto)
        aviso_grupo, _ = Aviso.objects.get_or_create(texto="Entrega del proyecto de Tecnología el viernes")
        aviso_grupo.grupos.set([g11])

        comunicado, _ = Comunicado.objects.get_or_create(
            titulo="Examen mañana viernes! Recordatorio importante.",
            defaults=dict(
                autor=profes["prof.diego"],
                tipo=Comunicado.Tipo.COMUNICADO,
                contenido=(
                    "Recuerden que el examen de tecnología se realizará el mañana viernes a las 8:00 am.\n\n"
                    "Es importante que estudien los temas vistos en clase y repasen los apuntes. "
                    "No se permiten dispositivos electrónicos durante el examen. ¡Buena suerte a todos!"
                ),
            ),
        )
        comunicado.grupos.set([g11])

        self.stdout.write(self.style.SUCCESS("Datos de ejemplo cargados."))
        self.stdout.write(f"  Estudiante (11°): juan.andres  /  {CLAVE}")
        self.stdout.write(f"  Profesor:         prof.diego   /  {CLAVE}")
        self.stdout.write(f"  Los enlaces de Teams son de relleno ({ENLACE_DEMO}): cámbielos en /admin.")

    def limpiar_demo_anterior(self):
        """Quita los grupos de la primera demostración (10-A y 10-B) y lo que colgaba de ellos."""
        borrados, _ = Grupo.objects.filter(nombre__in=["10-A", "10-B"]).delete()
        Asignatura.objects.filter(nombre="Sociales", clasehorario__isnull=True).delete()
        if borrados:
            self.stdout.write("  Se eliminaron los grupos de demostración 10-A y 10-B.")