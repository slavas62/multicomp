# -*- coding: utf-8 -*-

from django.contrib import admin
from .models import Mcbuilder  # Импорт модели
from django.contrib import messages
from django.utils.html import format_html

from filer.models import Folder
from filer.admin.folderadmin import FolderAdmin

# *** Задаем новые настройки FILER ***

admin.site.unregister(Folder) # Отменяем стандартную регистрацию, чтобы задать свои настройки FILER
@admin.register(Folder)
class CustomFolderAdmin(FolderAdmin):
    pass
Folder._meta.verbose_name = "Папка с исходниками" # Переименовываем названия в админке FILER
Folder._meta.verbose_name_plural = "Папки с исходниками"



# *** Управление в админке запуском функции создания композита для выбранного в списке ***

def run_script_on_selected(modeladmin, request, queryset):
    from django.apps import apps
    
    for obj in queryset:
        modeladmin.message_user(request, "Создается композит для объекта '" + obj.name + "'")
        print(f"Создается композит для объекта '{obj.name}'")

        myapp_config = apps.get_app_config('mcbuilder') # Получаем конфиг приложения
        result = myapp_config.mvc_build(obj)            # Вызываем функцию создания композита, которая находится в apps.py

        if obj.builded:
            modeladmin.message_user(request, "Выбранный композит успешно создан.", level=messages.SUCCESS)
        else:
            modeladmin.message_user(request, "Ошибка создания композита.", level=messages.ERROR)
            pass

        obj.save()
#        print(f"Админка получила: {result}")
    


# *** Регистрируем основную модель микросервиса в админке ***

run_script_on_selected.short_description = "Запустить создание выбранного композита"
@admin.register(Mcbuilder)
class McbuilderAdmin(admin.ModelAdmin):
    actions = [run_script_on_selected]  # Добавляем функцию запуска в список "Действий" админки

    list_display = ('name', 'get_folder_link', 'method', 'builded', 'get_result_link', 'date_created') # Поля в списке
    list_filter = ('name', 'mcfile')   # Фильтры справа
    search_fields = ('name', 'mcfile') # Поиск по полям
#    readonly_fields = ('mcfile',)
    
    def get_folder_link(self, obj):    # Ссылка на редактирование папки в виде её названия в списке композитов в админке
        if obj.files_folder:
            return format_html('<a href="/admin/filer/folder/{}/list" target="_blank"><b>' + obj.files_folder.name + '</b></a>', obj.files_folder.id)
        return "---"
    get_folder_link.short_description = 'Исходники'

    def get_result_link(self, obj):    # Ссылка на скачивание файла результата в списке композитов в админке
        if obj.mcfile:
            return format_html('<a href="/media/composite/{}" target="_blank"><b>Скачать</b></a>', obj.mcfile)
        return "---"
    get_result_link.short_description = 'Результат'

    def get_form(self, request, obj=None, **kwargs): # Подпись в админке созданного композита в виде ссылки на скачивание файла результата
        form = super().get_form(request, obj, **kwargs)
        if obj and obj.files_folder:
            form.base_fields['files_folder'].help_text = format_html('название папки с исходниками <a href="/admin/filer/folder/{}/list"><b>' + obj.files_folder.name + '</b></a>', obj.files_folder.id)
        if obj and obj.mcfile:
            form.base_fields['mcfile'].help_text = format_html('<a href="/media/composite/{}" target="_blank"><b>скачать файл</b></a>', obj.mcfile)
        return form
