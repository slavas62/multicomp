# -*- coding: utf-8 -*-

from django.contrib import admin
from .models import Mcbuilder  # Импорт модели
from django.contrib import messages
from django.utils.html import format_html

from filer.models import Folder
from filer.admin.folderadmin import FolderAdmin

# Задаем новые настройки FILER
admin.site.unregister(Folder) # Отменяем стандартную регистрацию, чтобы задать свои настройки FILER

@admin.register(Folder)
class CustomFolderAdmin(FolderAdmin):
    pass

Folder._meta.verbose_name = "Папка с исходниками" # Переименовываем названия в админке FILER
Folder._meta.verbose_name_plural = "Папки с исходниками"


# Управление запуском функции создания композита для выбранного в списке параметров создания
def run_script_on_selected(modeladmin, request, queryset):
    from django.apps import apps
    
    for obj in queryset:
        modeladmin.message_user(request, "Создается композит для объекта '" + obj.name + "'")
#        print(f'Имя папки: {obj.files_folder.name}')
        myapp_config = apps.get_app_config('mcbuilder') # Получаем конфиг приложения
        result = myapp_config.mvc_build(obj)            # Вызываем функцию создания композита, которая находится в apps.py

        if obj.builded:
            modeladmin.message_user(request, "Выбранный композит успешно создан.", level=messages.SUCCESS)
        else:
            modeladmin.message_user(request, "Ошибка создания композита.", level=messages.ERROR)
            pass
        obj.save()
#        print(f"Админка получила: {result}")
    


# Регистрируем основную модель микросервиса в админке
run_script_on_selected.short_description = "Запустить создание выбранного композита"
@admin.register(Mcbuilder)
class McbuilderAdmin(admin.ModelAdmin):
    actions = [run_script_on_selected]
    list_display = ('name', 'mcfile', 'get_folder_link', 'builded', 'date_created') # Поля в списке
    list_filter = ('name', 'mcfile')   # Фильтры справа
    search_fields = ('name', 'mcfile') # Поиск по полям
    
    def get_folder_link(self, obj):    # Ссылка на редактирование папки в виде её названия в списке созданных композитов в админке
        if obj.files_folder:
            return format_html('<a href="/admin/filer/folder/{}/list" target="_blank"><b>' + obj.files_folder.name + '</b></a>', obj.files_folder.id)
        return "---"
    get_folder_link.short_description = 'Имя папки с исходниками'

    def get_form(self, request, obj=None, **kwargs): # Подпись в админке созданного композита со ссылкой в виде названия папки на eё редактирование 
        form = super().get_form(request, obj, **kwargs)
        if obj and obj.files_folder:
            form.base_fields['files_folder'].help_text = format_html('название папки с исходниками <a href="/admin/filer/folder/{}/list"><b>' + obj.files_folder.name + '</b></a>', obj.files_folder.id)
        return form
