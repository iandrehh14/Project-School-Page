import re

from django.core.management.base import BaseCommand

from Main.models import Ciclo, Grupo


class Command(BaseCommand):
    help = "Asigna el ciclo a cada grupo según su grado (1-3, 4-5, 6-8, 9-11). Solo toca grupos sin ciclo."

    def handle(self, *args, **options):
        ciclos = list(Ciclo.objects.filter(es_transversal=False).order_by("orden")[:4])
        if len(ciclos) < 4:
            self.stderr.write("Primero ejecute: python manage.py cargar_biblioteca")
            return
        limites = [3, 5, 8, 11]  # último grado de cada ciclo

        for grupo in Grupo.objects.filter(ciclo__isnull=True):
            coincidencia = re.match(r"\d+", grupo.nombre)
            if not coincidencia:
                continue
            grado = int(coincidencia.group())
            for ciclo, limite in zip(ciclos, limites):
                if grado <= limite:
                    grupo.ciclo = ciclo
                    grupo.save()
                    self.stdout.write(f"  {grupo.nombre} → {ciclo.nombre}")
                    break
        self.stdout.write(self.style.SUCCESS("Ciclos asignados."))