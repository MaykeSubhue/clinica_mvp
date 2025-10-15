"""
URL configuration for clinica_mvp project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# clinica_mvp/urls.py
from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views

from clinic.views import (
    dashboard,
    export_appointments_csv,
    staff_signup,                   # existe no seu views.py
    protocols_dashboard,         # se você já criou
    patient_timeline,            # se você já criou
    staff_signup,              # comente/retire se NÃO criou essa view
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("dashboard/", dashboard, name="dashboard"),
    path("dashboard/export/", export_appointments_csv, name="export_csv"), # type: ignore

    path("login/",  auth_views.LoginView.as_view(
        template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="login"), name="logout"),

    path("staff/novo/", staff_signup, name="staff_signup"), 
    
    path("protocolos/", protocols_dashboard, name="protocols_dashboard"),
    path("pacientes/<int:patient_id>/linha-do-tempo/", patient_timeline, name="patient_timeline"),
]

