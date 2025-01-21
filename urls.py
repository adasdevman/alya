from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Assurez-vous que l'admin est défini avec un namespace unique
    path('admin/', admin.site.urls),  # Gardez celui-ci
    # Vos autres configurations d'URL
] 