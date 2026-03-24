# -*- coding: utf-8 -*-

from django.db import models

# Create your models here.
class Mcmethod(models.Model):
    name = models.CharField(u'Название', max_length=50, unique=True)
    alias = models.CharField(u'Псевдоним', max_length=20, help_text=u'англоязычный псевдоним метода')
    description = models.TextField(u'Описание', null=True, blank=True, help_text=u'описание метода')
   
    class Meta:
        verbose_name = u'Метод создания МВК'
        verbose_name_plural = u'Методы создания МВК'

    def __str__(self):
        return self.name