from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods


@require_http_methods(['GET', 'POST'])
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    error = None
    if request.method == 'POST':
        username = (request.POST.get('username') or '').strip()
        password = request.POST.get('password') or ''
        # Axes necesita el request para contar intentos
        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            request.session.cycle_key()
            return HttpResponseRedirect(reverse('dashboard'))
        error = 'Usuario o contraseña incorrectos.'

    return render(request, 'accounts/login.html', {'error': error})


@login_required
def logout_view(request):
    auth_logout(request)
    return redirect('login')
