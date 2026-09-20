from django.shortcuts import render

def home(request):
    return render(request, 'core/index.html')

def sobre(request):
    return render(request, 'core/sobre.html')

def servicos(request):
    return render(request, 'core/servicos.html')

def contato(request):
    return render(request, 'core/contato.html')