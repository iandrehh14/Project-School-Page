from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import UsuarioChangeForm, UsuarioCreationForm
from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    form = UsuarioChangeForm
    add_form = UsuarioCreationForm

    list_display = ("username", "documento", "email", "first_name", "last_name", "rol", "is_active")
    list_filter = ("rol", "is_active", "is_staff")
    search_fields = ("username", "documento", "email", "first_name", "last_name")
    ordering = ("last_name", "first_name")

    # Pantalla de edición: se añade un bloque con los datos del colegio
    fieldsets = UserAdmin.fieldsets + (
        ("Datos del colegio", {"fields": ("documento", "rol")}),
    )

    # Pantalla de creación
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Datos del colegio", {"fields": ("documento", "email", "first_name", "last_name", "rol")}),
    )