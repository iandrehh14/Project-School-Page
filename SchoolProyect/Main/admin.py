from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import UsuarioChangeForm, UsuarioCreationForm
from .models import Asignatura, Aviso, ClaseHorario, Comunicado, Grupo, Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    form = UsuarioChangeForm
    add_form = UsuarioCreationForm

    list_display = ("username", "documento", "email", "first_name", "last_name", "rol", "grupo", "is_active")
    list_filter = ("rol", "grupo", "is_active", "is_staff")
    search_fields = ("username", "documento", "email", "first_name", "last_name")
    ordering = ("last_name", "first_name")

    # Pantalla de edición: se añade un bloque con los datos del colegio
    fieldsets = UserAdmin.fieldsets + (
        ("Datos del colegio", {"fields": ("documento", "rol", "grupo")}),
    )

    # Pantalla de creación
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Datos del colegio", {"fields": ("documento", "email", "first_name", "last_name", "rol", "grupo")}),
    )


@admin.register(Grupo)
class GrupoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "cantidad_estudiantes")
    search_fields = ("nombre",)

    @admin.display(description="Estudiantes")
    def cantidad_estudiantes(self, obj):
        return obj.estudiantes.count()


@admin.register(Asignatura)
class AsignaturaAdmin(admin.ModelAdmin):
    list_display = ("nombre",)
    search_fields = ("nombre",)


@admin.register(ClaseHorario)
class ClaseHorarioAdmin(admin.ModelAdmin):
    list_display = ("grupo", "dia", "hora_inicio", "hora_fin", "asignatura", "profesor", "salon")
    list_filter = ("grupo", "dia", "profesor")
    search_fields = ("asignatura__nombre", "profesor__first_name", "profesor__last_name")
    ordering = ("grupo__nombre", "dia", "hora_inicio")
    list_select_related = ("grupo", "asignatura", "profesor")


@admin.register(Aviso)
class AvisoAdmin(admin.ModelAdmin):
    list_display = ("texto", "alcance", "visible_desde", "visible_hasta", "activo")
    list_filter = ("activo", "grupos")
    search_fields = ("texto",)
    filter_horizontal = ("grupos",)

    @admin.display(description="Para")
    def alcance(self, obj):
        return obj.destinatarios


@admin.register(Comunicado)
class ComunicadoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "tipo", "autor", "alcance", "publicado", "activo")
    list_filter = ("tipo", "activo", "grupos")
    search_fields = ("titulo", "contenido")
    filter_horizontal = ("grupos",)
    readonly_fields = ("autor",)

    @admin.display(description="Para")
    def alcance(self, obj):
        return obj.destinatarios

    def save_model(self, request, obj, form, change):
        # El autor es quien lo crea; no se puede falsear desde el formulario
        if not change or obj.autor_id is None:
            obj.autor = request.user
        super().save_model(request, obj, form, change)