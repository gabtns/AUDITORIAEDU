from django.shortcuts import render


def acerca(request):
    return render(request, 'core/acerca.html')
