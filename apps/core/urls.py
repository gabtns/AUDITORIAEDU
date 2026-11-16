from django.urls import path
from . import views

urlpatterns = [
    path('acerca/', views.acerca, name='acerca'),
]
