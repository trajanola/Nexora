from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('quem-somos/', views.sobre, name='sobre'),
    path('o-que-fazemos/', views.servicos, name='servicos'),
    path('fale-conosco/', views.contato, name='contato'),
]