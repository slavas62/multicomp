# -*- coding: utf-8 -*-

from django.contrib import admin
from .models import Mcbuilder  # Импорт модели
from django.utils.html import format_html

from filer.models import Folder
from filer.admin.folderadmin import FolderAdmin

# Отменяем стандартную регистрацию, чтобы задать свои настройки FILER
admin.site.unregister(Folder)
@admin.register(Folder)
class CustomFolderAdmin(FolderAdmin):
    pass
# Переименовываем названия в админке FILER
Folder._meta.verbose_name = "Папка с исходниками"
Folder._meta.verbose_name_plural = "Папки с исходниками"

# Регистрируем основною модель микросервиса
@admin.register(Mcbuilder)
class PostAdmin(admin.ModelAdmin):
    list_display = ('name', 'mcfile', 'get_folder_link', 'date_created') # Поля в списке
    list_filter = ('name', 'mcfile')                 # Фильтры справа
    search_fields = ('name', 'mcfile')               # Поиск по полям

    def get_folder_name(self, obj):
        return obj.files_folder.name if obj.files_folder else "Нет исходных данных"
    get_folder_name.short_description = 'Имя папки с исходниками'
    
    def get_folder_link(self, obj): # Ссылка на редактирование папки в виде её названия в списке созданных композитов в админке
        if obj.files_folder:
            return format_html('<a href="/admin/filer/folder/{}/list" target="_blank"><b>' + obj.files_folder.name + '</b></a>', obj.files_folder.id)
        return "---"
    get_folder_link.short_description = 'Имя папки с исходниками'
    
    def get_form(self, request, obj=None, **kwargs): # Подпись в админке созданного композита со ссылкой в виде названия папки на eё редактирование 
        form = super().get_form(request, obj, **kwargs)
        if obj and obj.files_folder:
            form.base_fields['files_folder'].help_text = format_html('название папки с исходниками <a href="/admin/filer/folder/{}/list"><b>' + obj.files_folder.name + '</b></a>', obj.files_folder.id)
        return form    