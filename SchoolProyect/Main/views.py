from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import render
from django.utils import timezone


from .models import (
    Aviso, ClaseHorario, Comunicado, EnlaceMateria, Espacio, Franja, Grupo, Usuario,
)




@login_required
def index(request):
    usuario = request.user
    hoy = timezone.localdate()

    # Horario de hoy: solo materias (sin «Trabajo autónomo» ni «Dir. de grupo»)
    clases = (
        ClaseHorario.objects.filter(dia=hoy.weekday(), asignatura__es_materia=True)
        .select_related("asignatura", "profesor", "grupo")
    )
    sin_grupo = False

    if usuario.is_superuser or usuario.rol == Usuario.Rol.ADMINISTRATIVO:
        clases = clases.none()
    elif usuario.rol == Usuario.Rol.PROFESOR:
        clases = clases.filter(profesor=usuario)
    elif usuario.grupo_id:
        clases = clases.filter(grupo_id=usuario.grupo_id)
    else:
        clases = clases.none()
        sin_grupo = True

    comunicados = (
        Comunicado.objects.filter(activo=True)
        .para(usuario)
        .select_related("autor")
        .prefetch_related("grupos")
        .order_by("-publicado")[:5]
    )
    avisos = Aviso.objects.vigentes().para(usuario).prefetch_related("grupos")[:6]

    return render(request, 'main/index.html', {
        'clases': clases,
        'comunicados': comunicados,
        'avisos': avisos,
        'hoy_iso': hoy.isoformat(),
        'sin_grupo': sin_grupo,
    })


@login_required
def schedule(request):
    """Cuadrícula de grados; cada uno abre su horario en una ventana emergente."""
    dias = ClaseHorario.Dia.choices
    franjas = list(Franja.objects.all())

    # Una sola consulta por tabla; luego se arma todo en memoria
    celdas = {}
    grupos_con_horario = set()
    for clase in ClaseHorario.objects.filter(franja__isnull=False).select_related("asignatura"):
        celdas[(clase.grupo_id, clase.franja_id, clase.dia)] = clase
        grupos_con_horario.add(clase.grupo_id)

    enlaces = {}
    for enlace in EnlaceMateria.objects.select_related("asignatura"):
        enlaces.setdefault(enlace.grupo_id, []).append(enlace)

    grados = []
    for grupo in Grupo.objects.select_related("director"):
        filas = []
        for franja in franjas:
            if franja.es_descanso:
                filas.append({"franja": franja, "descanso": True, "celdas": []})
            else:
                filas.append({
                    "franja": franja,
                    "descanso": False,
                    "celdas": [celdas.get((grupo.pk, franja.pk, dia)) for dia, _ in dias],
                })
        grados.append({
            "grupo": grupo,
            "filas": filas,
            "tiene_horario": grupo.pk in grupos_con_horario,
            "enlaces": enlaces.get(grupo.pk, []),
        })

    return render(request, 'main/schedule.html', {
        'grados': grados,
        'dias': dias,
        'espacios': Espacio.objects.all(),
    })


class LoginUsuarioView(LoginView):
    """
    Inicio de sesión con usuario, correo o documento
    (la búsqueda la hace Main/backends.py).
    """
    template_name = 'main/login.html'
    redirect_authenticated_user = True