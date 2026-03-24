
from django.shortcuts import render, redirect
from .forms import McbuilderForm

def model_form_upload(request):
    if request.method == 'POST':
        form = McbuilderForm(request.POST, request.FILES) # Обязательно request.FILES
        if form.is_valid():
            form.save()
            return redirect('home')
    else:
        form = McbuilderForm()
    return render(request, 'upload.html', {'form': form})
