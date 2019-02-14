from django.urls import path

from . import views

app_name = 'results'

urlpatterns= [
    path('', views.index, name='index'),
    path('order/<int:order>/',views.sweeps,name='sweeps'),
    path('sweep/<int:id>/',views.sweep,name='sweep'),
    path('run/<int:id>/',views.run,name='run'),    
]
