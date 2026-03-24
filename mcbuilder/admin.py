# -*- coding: utf-8 -*-

from django.contrib import admin
from .models import Mcbuilder  # Импорт модели

@admin.register(Mcbuilder)
class PostAdmin(admin.ModelAdmin):
    list_display = ('name', 'mcfile', 'date_created') # Поля в списке
    list_filter = ('name', 'mcfile')                 # Фильтры справа
    search_fields = ('name', 'mcfile')               # Поиск по полям