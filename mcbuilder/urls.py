from django.urls import path, include
from . import views

urlpatterns = [
    path('upload/', views.model_form_upload , name='upload_file_url'),
]
