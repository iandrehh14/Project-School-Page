import os
from datetime import timedelta
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms_material import MaterialForm, es_admin
from .models import AreaBiblioteca, Aviso, Grupo, Material, Usuario


def docente_requerido(vista):
    """Solo profesores y personal administrativo."""
    @login_required
    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        if not (es_admin(request.user) or request.user.rol == Usuario.Rol.PROFESOR):
            raise PermissionDenied
        return vista(request, *args, **kwargs)
    return envoltura


# ---------------------------------------------------------------- estudiantes
def biblioteca_area(request, pk):
    area = get_object_or_404(AreaBiblioteca.objects.select_related("ciclo"), pk=pk)
    materiales = Material.objects.filter(area=area).select_related("profesor").prefetch_related("grupos")
    if request.user.is_authenticated:
        materiales = materiales.para(request.user)

    q = request.GET.get("q", "").strip()
    grupo = request.GET.get("grupo", "")
    periodo = request.GET.get("periodo", "")
    tipo = request.GET.get("tipo", "")

    if q:
        materiales = materiales.filter(
            Q(titulo__icontains=q) | Q(descripcion__icontains=q)
            | Q(profesor__first_name__icontains=q) | Q(profesor__last_name__icontains=q)
        )
    if grupo.isdigit():
        materiales = materiales.filter(Q(grupos=int(grupo)) | Q(todo_ciclo=True))
    if periodo.isdigit():
        materiales = materiales.filter(periodo=int(periodo))
    if tipo in Material.Tipo.values:
        materiales = materiales.filter(tipo=tipo)

    pagina = Paginator(materiales.distinct(), 12).get_page(request.GET.get("page"))
    consulta = request.GET.copy()
    consulta.pop("page", None)

    grupos = Grupo.objects.all() if area.ciclo.es_transversal else Grupo.objects.filter(ciclo=area.ciclo)
    return render(request, "main/biblioteca_area.html", {
        "area": area, "pagina": pagina, "grupos": grupos, "consulta": consulta.urlencode(),
        "filtros": {"q": q, "grupo": grupo, "periodo": periodo, "tipo": tipo},
        "tipos": Material.Tipo.choices, "periodos": range(1, 5),
        "hay_filtros": bool(q or grupo or periodo or tipo),
    })


@login_required
def material_descargar(request, pk):
    material = get_object_or_404(Material.objects.para(request.user), pk=pk)
    if not material.archivo:
        raise Http404
    try:
        archivo = material.archivo.open("rb")
    except FileNotFoundError:
        raise Http404
    return FileResponse(archivo, as_attachment=True,
                        filename=material.nombre_archivo or os.path.basename(material.archivo.name))


# ------------------------------------------------------------------ profesores
@docente_requerido
def mis_materiales(request):
    materiales = Material.objects.select_related("area__ciclo").prefetch_related("grupos")
    if not es_admin(request.user):
        materiales = materiales.filter(profesor=request.user)
    sin_ciclo = (not es_admin(request.user)
                 and Grupo.objects.filter(clases__profesor=request.user, ciclo__isnull=True).exists())
    return render(request, "main/mis_materiales.html", {"materiales": materiales, "sin_ciclo": sin_ciclo})


@docente_requerido
def material_guardar(request, pk=None):
    material = None
    if pk:
        consulta = Material.objects.all() if es_admin(request.user) else Material.objects.filter(profesor=request.user)
        material = get_object_or_404(consulta, pk=pk)

    inicial = {"area": request.GET.get("area")} if material is None else None
    form = MaterialForm(request.POST or None, request.FILES or None,
                        instance=material, usuario=request.user, initial=inicial)
    if request.method == "POST" and form.is_valid():
        nuevo = material is None
        objeto = form.save(commit=False)
        if nuevo:
            objeto.profesor = request.user
        objeto.save()
        form.save_m2m()

        if nuevo and form.cleaned_data.get("avisar"):
            aviso = Aviso.objects.create(
                texto=f"Nuevo material de {objeto.area.nombre}: {objeto.titulo}"[:250],
                visible_hasta=timezone.localdate() + timedelta(days=7),
            )
            if not objeto.area.ciclo.es_transversal:
                destino = Grupo.objects.filter(ciclo=objeto.area.ciclo) if objeto.todo_ciclo else objeto.grupos.all()
                aviso.grupos.set(destino)

        messages.success(request, "Material guardado." if not nuevo else "Material publicado.")
        return redirect("mis_materiales")

    return render(request, "main/material_form.html", {"form": form, "material": material})


@docente_requerido
def material_borrar(request, pk):
    consulta = Material.objects.all() if es_admin(request.user) else Material.objects.filter(profesor=request.user)
    material = get_object_or_404(consulta, pk=pk)
    if request.method == "POST":
        material.delete()
        messages.success(request, "Material eliminado.")
        return redirect("mis_materiales")
    return render(request, "main/material_borrar.html", {"material": material})