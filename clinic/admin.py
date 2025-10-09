from django.contrib import admin
from .models import Patient, Provider, Diagnosis, Appointment, Encounter, Vitals

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("full_name", "sex", "birth_date", "created_at")
    search_fields = ("full_name",)

@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ("full_name", "crm", "specialty")
    list_filter = ("specialty",)
    search_fields = ("full_name", "crm")

@admin.register(Diagnosis)
class DiagnosisAdmin(admin.ModelAdmin):
    list_display = ("code", "description")
    search_fields = ("code", "description")

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("patient", "provider", "scheduled_at", "status")
    list_filter = ("status", "provider__specialty")
    date_hierarchy = "scheduled_at"
    search_fields = ("patient__full_name", "provider__full_name")

@admin.register(Encounter)
class EncounterAdmin(admin.ModelAdmin):
    list_display = ("patient", "provider", "check_in", "check_out")
    date_hierarchy = "check_in"
    list_filter = ("provider__specialty",)

@admin.register(Vitals)
class VitalsAdmin(admin.ModelAdmin):
    list_display = ("encounter", "height_cm", "weight_kg", "systolic", "diastolic", "heart_rate")
