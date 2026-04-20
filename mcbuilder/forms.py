from django import forms
from .models import Mcbuilder

class McbuilderForm(forms.ModelForm):
    class Meta:
        model = Mcbuilder
#        fields = '__all__'
        fields = ('name', 'mcfile', 'files_folder', 'method', 'description',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['files_folder'].required = False  # Сделать поле необязательным