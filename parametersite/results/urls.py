from django.urls import path

from . import views

app_name = 'results'

urlpatterns= [
    path('', views.IndexView.as_view(), name='index'),
]
