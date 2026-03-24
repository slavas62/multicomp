# -*- coding: utf-8 -*-

from django.contrib import admin
from .models import Mcmethod  # Импорт модели

@admin.register(Mcmethod)
class PostAdmin(admin.ModelAdmin):
    list_display = ('name', 'alias', 'description') # Поля в списке
    list_filter = ('name', 'alias')                 # Фильтры справа
    search_fields = ('name', 'alias')               # Поиск по полям