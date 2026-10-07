from django.core.management.base import BaseCommand

from Main.models import AreaBiblioteca, Ciclo

# (nombre, grados, descripción, es_transversal, orden)
CICLOS = [
    ("Ciclo inicial", "Grado 1° - 3°", "Contenidos básicos para los primeros años de educación", False, 1),
    ("Ciclo primaria avanzada", "Grado 4° - 5°", "Contenidos avanzados para el cierre de la primaria", False, 2),
    ("Ciclo secundaria básica", "Grado 6° - 8°", "Contenidos básicos para los primeros años de secundaria", False, 3),
    ("Ciclo media", "Grado 9° - 11°", "Contenidos avanzados para el cierre de la secundaria", False, 4),
    ("Contenidos transversales", "Todos los grados", "Material que aplica a toda la institución", True, 5),
]

# (nombre, detalle, ícono)
AREAS = [
    ("Matemáticas", "", "matematicas"),
    ("Ciencias Naturales", "", "biologia"),
    ("Sociales y Humanidades", "Ciencias sociales · Ética · Religión", "sociales"),
    ("Lenguaje", "Castellano · Inglés", "lengua"),
    ("Tecnología", "", "tecnologia"),
    ("Educación Física", "", "educacion_fisica"),
]


class Command(BaseCommand):
    help = "Crea los 5 ciclos de la biblioteca y las áreas de los ciclos 1 a 4 (no duplica ni pisa lo editado)."

    def handle(self, *args, **options):
        for nombre, grados, desc, transversal, orden in CICLOS:
            ciclo, _ = Ciclo.objects.get_or_create(
                nombre=nombre,
                defaults=dict(grados=grados, descripcion=desc, es_transversal=transversal, orden=orden),
            )
            if transversal:
                continue  # el central no tiene áreas todavía
            for posicion, (area, detalle, icono) in enumerate(AREAS, start=1):
                # El ciclo secundaria básica estudia Matemáticas-Geometría
                if area == "Matemáticas" and orden == 3:
                    area = "Matemáticas - Geometría"
                AreaBiblioteca.objects.get_or_create(
                    ciclo=ciclo, nombre=area,
                    defaults=dict(detalle=detalle, icono=icono, orden=posicion),
                )
        self.stdout.write(self.style.SUCCESS("Biblioteca cargada."))