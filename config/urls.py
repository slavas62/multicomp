"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('mcbuilder/', include('mcbuilder.urls')), # Все ссылки из приложения mcbuilder теперь начинаются с /mcbuilder/
    path('filer/', include('filer.urls')), # Ссылки приложения FILER начинаются с /filer/
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Изменяем заголовки микросервиса
admin.site.site_header = "Микросервис мультивременных композитов "  # Заголовок админки вверху
admin.site.index_title = "Добро пожаловать в Микросервис" # Заголовок на главной странице админки
admin.site.site_title = "MultiComp"             # Заголовок во вкладке браузера

