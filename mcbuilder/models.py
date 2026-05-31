# -*- coding: utf-8 -*-

from django.db import models
from mcmethod.models import Mcmethod
from filer.fields.folder import FilerFolderField
from django.contrib.auth.models import User

# Create your models here.
class Mcbuilder(models.Model):

    METHOD_CHOICES = [         # Определение вариантов методов агрегации 'median', 'mean', 'max', 'min для метода многовременного композита
        ('median', 'Медиана'),
        ('mean', 'Среднее'),
        ('max', 'Максимум'),
        ('min', 'Минимум'),
    ]

    METHOD_CTYPES = [         # Расширенная версия с поддержкой многополосных файлов и разными типами композитов
        ('range', 'Размах по временному ряду'),
        ('std', 'Стандартное отклонение'),
        ('coefficient_of_variation', 'Коэффициент вариации'),
        ('difference_sum', 'Cумма абсолютных разностей'),
    ]

    BANDS_COMBIN = [         # Выбор каналов для расчета разностного композита
        ('Red', 'Красный канал'),
        ('Green', 'Зеленый канал'),
        ('Blue', 'Синий канал'),
        ('RGB', 'Все каналы'),
    ]

    name = models.CharField(u'Название', max_length=50, help_text=u'название мультивременного композита')
    mcfile = models.CharField(u'Имя файла результата', null=True, blank=True, max_length=255, help_text=u'путь к файлу результата')
    files_folder = FilerFolderField(
        null=True,                 # Разрешить отсутствие выбора
        blank=True,                # Разрешаем пустое поле папки с файлами, для возможности добавления потом
        on_delete=models.SET_NULL, # CASCADE - При удалении папки удалятся все связанные объекты
        verbose_name=u"Папка с исходниками",
        help_text=u"название папки"
    )
    date_created = models.DateTimeField(u'Дата создания', auto_now_add=True, help_text=u'дата создания выходного файла')
    method = models.ForeignKey(Mcmethod, verbose_name =u'Методы МВК', default=4, on_delete=models.PROTECT)
    agregat = models.CharField(u'Метод агрегации', max_length=10, choices=METHOD_CHOICES, default='median', help_text=u'для многовременного композита')
    ctypes = models.CharField(u'Тип композита', max_length=30, choices=METHOD_CTYPES, default='range', help_text=u'с поддержкой многоканальных файлов')
    bands = models.CharField(u'Рабочий канал', max_length=30, choices=BANDS_COMBIN, default='2', help_text=u'исходные каналы для создания композита')
    resampl = models.BooleanField(u'Выполнить ресемплинг', default=False, help_text=u'привести снимки к единой проекции, размерам, разрешению и extent.')
    description = models.TextField(u'Описание', null=True, blank=True, help_text=u'описание результата')
    builded = models.BooleanField(u'Выполнено', default=False, help_text=u'композит успешно создан')
    author = models.ForeignKey(User, verbose_name =u'Автор', on_delete=models.CASCADE, default=1, editable=False)

    class Meta:
        verbose_name = u'параметры создания МВК'
        verbose_name_plural = u'параметры создания МВК'

    def __str__(self):
        return self.name