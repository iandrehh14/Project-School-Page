from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import render
from django.utils import timezone

from .models import Aviso, ClaseHorario, Comunicado, Usuario


@login_required
def index(request):
    usuario = request.user
    hoy = timezone.localdate()

    # Horario de hoy: según el rol de quien mira
    clases = ClaseHorario.objects.filter(dia=hoy.weekday()).select_related("asignatura", "profesor", "grupo")
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
    return render(request, 'main/schedule.html')


class LoginUsuarioView(LoginView):
    """
    Inicio de sesión con usuario, correo o documento
    (la búsqueda la hace Main/backends.py).
    """
    template_name = 'main/login.html'
    redirect_authenticated_user = True