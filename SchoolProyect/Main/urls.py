from django.contrib.auth.views import LogoutView
from django.urls import path


from . import views

from . import contenido_views

from . import biblioteca_views

urlpatterns = [
    path('', views.index, name='index'),
    path('schedule/', views.schedule, name='schedule'),
    path('login/', views.LoginUsuarioView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('biblioteca/', biblioteca_views.biblioteca, name='biblioteca'),
    path('biblioteca/ciclo/<int:pk>/', biblioteca_views.biblioteca_ciclo, name='biblioteca_ciclo'),
    path('biblioteca/area/<int:pk>/', contenido_views.biblioteca_area, name='biblioteca_area'),
    path('biblioteca/descargar/<int:pk>/', contenido_views.material_descargar, name='material_descargar'),
    path('materiales/', contenido_views.mis_materiales, name='mis_materiales'),
    path('materiales/nuevo/', contenido_views.material_guardar, name='material_nuevo'),
    path('materiales/<int:pk>/editar/', contenido_views.material_guardar, name='material_editar'),
    path('materiales/<int:pk>/borrar/', contenido_views.material_borrar, name='material_borrar'),
]