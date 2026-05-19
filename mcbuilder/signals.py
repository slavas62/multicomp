from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models.signals import post_save
from django.dispatch import receiver
from filer.models import Folder, FolderPermission

User = get_user_model()

@receiver(post_save, sender=User)
def create_user_folder(sender, instance, created, **kwargs):
    """
    При создании нового пользователя автоматически:
    1. Создаёт для него личную папку в корне filer.
    2. Выдаёт права на чтение, редактирование и добавление файлов/папок.
    """
    if not created:
        return  # Обрабатываем только создание, не обновление

    # --- 1. Добавление в группу ---
    group_name = getattr(
        settings,
        'DEFAULT_USER_GROUP',
        'Filer Users'  # Название вашей группы по умолчанию
    )

    try:
        group = Group.objects.get(name=group_name)
        instance.groups.add(group)
    except Group.DoesNotExist:
        # Группа не найдена — можно залогировать или проигнорировать
        pass

    # --- 2. Создание личной папки ---
    folder_name = getattr(
        settings,
        'FILER_USER_FOLDER_NAME',
#        f'user_{instance.username}'
        f'{instance.username}'    # Имя папки — можно настроить под себя
    )

    # Проверяем, нет ли уже такой папки (на всякий случай)
    if Folder.objects.filter(
        name=folder_name,
        parent__isnull=True,  # Корневая папка
        owner=instance
    ).exists():
        return

    # Создаём папку в корне (parent=None)
    user_folder = Folder.objects.create(
        name=folder_name,
        owner=instance,        # Владелец папки
        parent=None            # Корень хранилища
    )

    # Выдаём пользователю права на эту папку
    FolderPermission.objects.create(
        folder=user_folder,
        user=instance,
        can_read=True,          # Видеть папку и содержимое
        can_edit=True,          # Переименовывать, перемещать
        can_add_children=True,  # Создавать вложенные папки и файлы
#        can_delete=True,        # Удалять (при необходимости)
    )