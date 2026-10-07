from django import forms
from django.db.models import Q

from .models import AreaBiblioteca, Grupo, Material, Usuario


def es_admin(usuario):
    return usuario.is_superuser or usuario.rol == Usuario.Rol.ADMINISTRATIVO


class MaterialForm(forms.ModelForm):
    avisar = forms.BooleanField(
        label="Avisar en Inicio durante 7 días", required=False, initial=True,
    )

    class Meta:
        model = Material
        fields = ["titulo", "descripcion", "tipo", "periodo", "area", "grupos", "todo_ciclo", "archivo", "enlace"]
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 3}),
            "grupos": forms.CheckboxSelectMultiple,
            "archivo": forms.FileInput,
            "enlace": forms.URLInput(attrs={"placeholder": "https://…"}),
        }

    def __init__(self, *args, usuario, **kwargs):
        super().__init__(*args, **kwargs)
        grupos = Grupo.objects.all() if es_admin(usuario) else Grupo.objects.filter(clases__profesor=usuario).distinct()
        areas = AreaBiblioteca.objects.select_related("ciclo")
        if not es_admin(usuario):
            ciclos = grupos.exclude(ciclo__isnull=True).values("ciclo")
            areas = areas.filter(Q(ciclo__in=ciclos) | Q(ciclo__es_transversal=True))

        self.fields["area"].queryset = areas
        self.fields["grupos"].queryset = grupos
        self.fields["grupos"].required = False
        self.fields["area"].empty_label = "Elija un área…"
        self.fields["area"].label_from_instance = lambda a: f"{a.nombre} · {a.ciclo.nombre}"
        if self.instance.pk:
            del self.fields["avisar"]

        # Datos para que el navegador oculte los grupos que no son del ciclo del área
        self.mapa = {
            "areas": {a.pk: {"ciclo": a.ciclo_id, "transversal": a.ciclo.es_transversal} for a in areas},
            "grupos": {g.pk: g.ciclo_id for g in grupos},
        }

    def clean(self):
        datos = super().clean()
        area = datos.get("area")
        if area:
            if area.ciclo.es_transversal:
                datos["grupos"] = Grupo.objects.none()
                datos["todo_ciclo"] = True
            else:
                grupos = datos.get("grupos")
                if not datos.get("todo_ciclo") and not grupos:
                    self.add_error("grupos", "Elija al menos un grupo o marque «Todo el ciclo».")
                elif grupos and any(g.ciclo_id != area.ciclo_id for g in grupos):
                    self.add_error("grupos", "Hay grupos que no pertenecen al ciclo de esta área.")

        subido = self.files.get("archivo")
        enlace = datos.get("enlace")
        if subido and enlace:
            raise forms.ValidationError("Elija un archivo o un enlace, no ambos.")
        if enlace and not subido:
            datos["archivo"] = False  # el enlace reemplaza al archivo anterior
        elif not subido and not enlace and not self.instance.archivo:
            raise forms.ValidationError("Suba un archivo o pegue un enlace.")
        return datos