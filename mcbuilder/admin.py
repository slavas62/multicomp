# -*- coding: utf-8 -*-

from django.contrib import admin
from .models import Mcbuilder  # Импорт модели
from django.contrib import messages
from django.utils.html import format_html

from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from filer.models import Folder, ThumbnailOption
from filer.admin.folderadmin import FolderAdmin

import os


# *** Задаем новые настройки списка пользователей ***
class CustomUserAdmin(UserAdmin):
    def is_superuser_status(self, obj):      # Добавляем метод для красивого вывода статуса администратора
        if obj.is_superuser:
            return format_html('<span style="color: green;">✔️ Да</span>')
        return format_html('<span style="color: red;">❌ Нет</span>')

    is_superuser_status.short_description = "Администратор"

    # Выводим нужные поля в списке
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_superuser_status",
    )
# Отменяем стандартную регистрацию и регистрируем заново с кастомным классом
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


# *** Задаем новые настройки FILER ***
try:                          # Отменяем отображение в админке стандартной модели "Опции миниатюры"
    admin.site.unregister(ThumbnailOption)
except admin.sites.NotRegistered:
    pass

admin.site.unregister(Folder) # Отменяем стандартную регистрацию, чтобы задать свои настройки FILER
class CustomFolderAdmin(FolderAdmin):

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Показываем только папки, где владелец – текущий пользователь, плюс папки без владельца (например, общие)
        return qs.filter(owner=request.user)

    def save_model(self, request, obj, form, change):
        if not change:  # При создании принудительно ставим владельца
            obj.owner = request.user
        super().save_model(request, obj, form, change)

Folder._meta.verbose_name = "Папка с исходниками" # Переименовываем названия в админке FILER
Folder._meta.verbose_name_plural = "Папки с исходниками"
admin.site.register(Folder, CustomFolderAdmin)


# *** Управление в админке запуском функции создания композита для выбранного в списке ***
def run_script_create_composit(modeladmin, request, queryset):
    from django.apps import apps
    
    for obj in queryset:
        modeladmin.message_user(request, "Создается композит для объекта '" + obj.name + "'")
        print(f"Создается композит для объекта '{obj.name}'")

        myapp_config = apps.get_app_config('mcbuilder')   # Получаем конфиг приложения
        result = myapp_config.mvc_build(modeladmin, request, obj)  # Вызываем функцию создания композита, которая находится в apps.py

        if obj.builded:
            modeladmin.message_user(request, f"Композит {obj.mcfile} успешно создан.", level=messages.SUCCESS)
        else:
            modeladmin.message_user(request, f"Ошибка создания композита!", level=messages.ERROR)
            pass
        obj.save()
# Удаление папки исходных данных из параметров создания композита
def run_clear_folder_field(modeladmin, request, queryset):
    queryset.update(files_folder=None)
    queryset.update(builded=False)
    queryset.update(mcfile=None)


# *** Регистрируем основную модель микросервиса mcbuilder в админке ***
run_clear_folder_field.short_description = "Удалить папку данных для выбранных параметров"
run_script_create_composit.short_description = "Запустить создание выбранных композитов"
@admin.register(Mcbuilder)
class McbuilderAdmin(admin.ModelAdmin):
    actions = [run_clear_folder_field, run_script_create_composit, ]  # Добавляем функцию запуска в список "Действий" админки

    list_display = ('name', 'get_folder_link', 'method', 'builded', 'geotron', 'get_result_link', 'date_created', 'author') # Поля в списке
    list_filter = ('builded', 'geotron', 'author')   # Фильтры справа
    search_fields = ('name', 'mcfile') # Поиск по полям
    readonly_fields = ( 'builded', 'author',)
    
    class Media:            # Подключаем JS для визуализации поля метода агрегации при выборе метода многовременного композита
        js = (
            'mcbuilder/js/method_fields.js',
            'mcbuilder/js/lock_action.js',
            'mcbuilder/js/change_title_filer.js',
        )
        css = {
            'all': ('mcbuilder/css/filer_widget.css',)
        }

# Автоматическое сохранение автора новых параметров создания композитв
    def save_model(self, request, obj, form, change):
        obj.builded = False
        obj.mcfile = None
        if not change:                  # Только при создании нового объекта
            obj.author = request.user
        super().save_model(request, obj, form, change)
# Запрос данных только для зарегистрированного пользователя
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:   # Суперпользователь видит всё
            return qs
        return qs.filter(author=request.user)
# Ограничение прав на изменение и удаление чужих объектов
    def has_change_permission(self, request, obj=None):
        if obj is not None and not request.user.is_superuser and obj.author != request.user:   # Суперпользователь видит всё
            return False
        return super().has_change_permission(request, obj)
    def has_delete_permission(self, request, obj=None):
        if obj is not None and not request.user.is_superuser and obj.author != request.user:   # Суперпользователь видит всё
            return False
        return super().has_delete_permission(request, obj)
    def has_view_permission(self, request, obj=None):
        if obj is not None and not request.user.is_superuser and obj.author != request.user:   # Суперпользователь видит всё
            return False
        return super().has_view_permission(request, obj)

    def get_folder_link(self, obj):    # Ссылка на редактирование папки в виде её названия в списке композитов в админке
        if obj.files_folder:
            return format_html('<a href="/admin/filer/folder/{}/list" target="_blank"><b>' + obj.files_folder.name + '</b></a>', obj.files_folder.id)
        return "---"
    get_folder_link.short_description = 'Исходники'

    def get_result_link(self, obj):    # Ссылка на скачивание файла результата в списке композитов в админке
        if obj.mcfile:
            outdir = os.environ.get('GEOSERVER_OUTDIR_MULTICOMP', 'media/composite/')
            return format_html('<a href="/' + outdir +'{}" target="_blank"><b>Скачать</b></a>', obj.mcfile)
        return "---"
    get_result_link.short_description = 'Результат'

    def get_form(self, request, obj=None, **kwargs): # Подпись в админке созданного композита в виде ссылки на скачивание файла результата
        form = super().get_form(request, obj, **kwargs)
        if obj and obj.files_folder:
            form.base_fields['files_folder'].help_text = format_html('название папки с исходниками <a href="/admin/filer/folder/{}/list"><b>' + obj.files_folder.name + '</b></a>', obj.files_folder.id)
        if obj and obj.mcfile:
            outdir = os.environ.get('GEOSERVER_OUTDIR_MULTICOMP', 'media/composite/')
            form.base_fields['mcfile'].help_text = format_html('<a href="/' + outdir +'{}" target="_blank"><b>скачать файл</b></a>', obj.mcfile)
        return form
