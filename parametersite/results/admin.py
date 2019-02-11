from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register(Parameter)
admin.site.register(Category)
admin.site.register(Dataset)
admin.site.register(Sweep)
admin.site.register(SweepParameter)
admin.site.register(Run)
admin.site.register(RunValue)
admin.site.register(Profile)
admin.site.register(LocalResult)
admin.site.register(LocalResultScore)
admin.site.register(GlobalResult)
admin.site.register(GlobalResultScore)
