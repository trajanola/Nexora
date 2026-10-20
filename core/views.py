from django.shortcuts import render
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.contrib.auth import authenticate, login as auth_login
from django.views import View

def home(request):
    return render(request, 'core/index.html')

def sobre(request):
    return render(request, 'core/sobre.html')

def servicos(request):
    return render(request, 'core/servicos.html')

def contato(request):
    return render(request, 'core/contato.html')


class Cadastro(View):
    def get(self, request):
        return render(request, 'core/Cadastro.html')

    def post(self, request):
        if User.objects.filter(username=request.POST.get('nome_usuario')).exists():
            return HttpResponse("outro usuario ja possui este nome")

        usuario = User.objects.create_user(
            username = request.POST.get('nome_usuario'),
            email = request.POST.get('email_usuario'),
            password = request.POST.get('senha_usuario')
        ) 
        return HttpResponse("Usuario cadastrado")

class Logar(View):
    def get(self, request):
        return render(request, 'core/Login.html')

    def post(self, request):
        insert_user = request.POST.get("nome_usuario")
        insert_password = request.POST.get("senha_usuario")

        user = authenticate(request, username=insert_user, password=insert_password)

        if user is not None:
            auth_login(request, user)
            return HttpResponse("login realizado")
        else:
            return HttpResponse("falha no login, usuario ou senha inválidos")




