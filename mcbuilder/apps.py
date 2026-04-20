from django.apps import AppConfig

class McbuilderConfig(AppConfig):
    name = 'mcbuilder'
    verbose_name = 'Создание МВК'

    def mvc_build(self, obj):

        obj.builded = True
        return obj.builded