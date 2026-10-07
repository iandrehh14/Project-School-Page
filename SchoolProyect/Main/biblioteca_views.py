from django.shortcuts import get_object_or_404, render

from .models import Ciclo


def biblioteca(request):
    """Portada de la biblioteca: los ciclos (4 a los lados y el transversal al centro)."""
    ciclos = list(Ciclo.objects.all())
    laterales = [c for c in ciclos if not c.es_transversal]
    centro = next((c for c in ciclos if c.es_transversal), None)
    # Orden en la cuadrícula: laterales en su orden y el central intercalado vía CSS
    return render(request, "main/biblioteca.html", {"laterales": laterales, "centro": centro})


def biblioteca_ciclo(request, pk):
    """Áreas de un ciclo."""
    ciclo = get_object_or_404(Ciclo, pk=pk)
    return render(request, "main/biblioteca_ciclo.html", {"ciclo": ciclo, "areas": ciclo.areas.all()})