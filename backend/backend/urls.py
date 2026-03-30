from django.contrib import admin
from django.urls import path
from core.api import api as core_api 

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/',core_api.urls),
]
