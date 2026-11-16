from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(url='/login/', permanent=False)),
    path('', include('apps.accounts.urls')),
    path('', include('apps.registros.urls')),
    path('', include('apps.core.urls')),
]
