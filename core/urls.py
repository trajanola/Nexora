from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('quem-somos/', views.sobre, name='sobre'),
    path('o-que-fazemos/', views.servicos, name='servicos'),
    path('fale-conosco/', views.contato, name='contato'),
    path('cadastro/', views.Cadastro.as_view(), name='cadastro'),
    path('login/', views.Logar.as_view(), name='login'),
    path('logout/', views.Logout.as_view(), name='logout'),
    path('conta/excluir/', views.ExcluirConta.as_view(), name='excluir_conta'),
    path('dispositivos/', views.DispositivoListView.as_view(), name='dispositivo_lista'),
    path('dispositivos/novo/', views.DispositivoCreateView.as_view(), name='dispositivo_novo'),
    path('dispositivos/<int:pk>/', views.DispositivoDetailView.as_view(), name='dispositivo_detalhe'),
    path('api/leituras/', views.registrar_leitura, name='api_leitura'),
    path('painel/', views.Painel.as_view(), name='painel'),
    path('parametros/', views.ParametrosView.as_view(), name='parametros'),
]