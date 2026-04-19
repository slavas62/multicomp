# -*- coding: utf-8 -*-

from django.db import models
from mcmethod.models import Mcmethod
from filer.fields.folder import FilerFolderField

# Create your models here.
class Mcbuilder(models.Model):
    name = models.CharField(u'Название', max_length=50, help_text=u'название мультивременного композита')
    mcfile = models.CharField(u'Имя файла', max_length=20, help_text=u'англоязычное имя выходного файла')
#    file = models.FileField(u'Имя файла', upload_to='files/%Y%m%d/', null=True, blank=True)
    files_folder = FilerFolderField(
        null=True,           # Разрешить отсутствие выбора
        blank=True, # Разрешаем пустое поле папки с файлами, для возможности добавления потом
        on_delete=models.SET_NULL, # CASCADE - При удалении папки удалятся все связанные объекты
        verbose_name=u"Папка с исходниками",
        help_text=u"название папки"
    )
    date_created = models.DateTimeField(u'Дата создания', auto_now_add=True, help_text=u'дата создания выходного файла')
    method = models.ForeignKey(Mcmethod, verbose_name =u'Методы МВК', on_delete=models.PROTECT)
    description = models.TextField(u'Описание', null=True, blank=True, help_text=u'описание результата')
   
    class Meta:
        verbose_name = u'cервис создания МВК'
        verbose_name_plural = u'cервис создания МВК'
 
    def __str__(self):
        return self.name        