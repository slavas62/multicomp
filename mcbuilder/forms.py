from django import forms
from .models import Mcbuilder

class McbuilderForm(forms.ModelForm):
    class Meta:
        model = Mcbuilder
        fields = ('name', 'mcfile', 'files_folder', 'method', 'description',)
