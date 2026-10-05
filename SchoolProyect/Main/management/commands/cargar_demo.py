from datetime import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from Main.models import Asignatura, Aviso, ClaseHorario, Comunicado, Grupo, Usuario

CLAVE = "Colegio2026!"


class Command(BaseCommand):
    help = "Carga datos de ejemplo (grupos, profesores, horario, avisos y comunicados). Solo para desarrollo."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Este comando es solo para desarrollo (DEBUG debe ser True).")

        g10a, _ = Grupo.objects.get_or_create(nombre="10-A")
        g10b, _ = Grupo.objects.get_or_create(nombre="10-B")

        def asignatura(nombre):
            return Asignatura.objects.get_or_create(nombre=nombre)[0]

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
            return u

        P = Usuario.Rol.PROFESOR
        daniel = usuario("prof.daniel", "1000000011", "Daniel", "Gómez", P)
        mariana = usuario("prof.mariana", "1000000012", "Mariana", "Ríos", P)
        yeison = usuario("prof.yeison", "1000000013", "Yeison", "Castaño", P)
        jennifer = usuario("prof.jennifer", "1000000014", "Jennifer", "Mejía", P)
        diego = usuario("prof.diego", "1000000015", "Diego Andres", "Ocampo", P)
        juan = usuario("juan.andres", "1000000001", "Juan Andres", "Rodríguez", Usuario.Rol.ESTUDIANTE, g10a)

        # Horario de 10-A: igual de lunes a viernes
        bloques_10a = [
            (time(7), time(9), "Matemáticas", daniel),
            (time(9), time(11), "Química", mariana),
            (time(11), time(13), "Sociales", yeison),
            (time(14), time(16), "Ed. Física", jennifer),
            (time(16), time(17), "Tecnología", diego),
        ]
        bloques_10b = [
            (time(7), time(9), "Tecnología", diego),
            (time(9), time(11), "Matemáticas", daniel),
        ]
        for grupo, bloques in ((g10a, bloques_10a), (g10b, bloques_10b)):
            for dia in range(5):
                for inicio, fin, nombre, profesor in bloques:
                    ClaseHorario.objects.get_or_create(
                        grupo=grupo, dia=dia, hora_inicio=inicio,
                        defaults=dict(hora_fin=fin, asignatura=asignatura(nombre), profesor=profesor),
                    )

        # Avisos: tres para todo el colegio y uno solo para 10-A
        for texto in (
            "Semanas de vacaciones del 19 de junio al 14 de julio",
            "Pre Informe el próximo viernes después de vacaciones",
            "Reunión de padres el viernes 7 de junio",
        ):
            Aviso.objects.get_or_create(texto=texto)
        aviso_grupo, _ = Aviso.objects.get_or_create(texto="Entrega del proyecto de Tecnología el viernes")
        aviso_grupo.grupos.set([g10a])

        # Comunicado de ejemplo
        com, _ = Comunicado.objects.get_or_create(
            titulo="Examen mañana viernes! Recordatorio importante.",
            defaults=dict(
                autor=diego,
                tipo=Comunicado.Tipo.COMUNICADO,
                contenido=(
                    "Recuerden que el examen de tecnología se realizará el mañana viernes a las 8:00 am.\n\n"
                    "Es importante que estudien los temas vistos en clase y repasen los apuntes. "
                    "No se permiten dispositivos electrónicos durante el examen. ¡Buena suerte a todos!"
                ),
            ),
        )
        com.grupos.set([g10a, g10b])

        self.stdout.write(self.style.SUCCESS("Datos de ejemplo cargados."))
        self.stdout.write(f"  Estudiante: juan.andres  /  {CLAVE}")
        self.stdout.write(f"  Profesor:   prof.diego   /  {CLAVE}")