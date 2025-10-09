from django.db import models
from decimal import Decimal



class Diagnosis(models.Model):
    code = models.CharField(max_length=10)  # ex: J06.9
    description = models.CharField(max_length=200)

    def __str__(self): 
        return f"{self.code} - {self.description}"

class ProcedureCategory(models.Model):
    name = models.CharField(max_length=80, unique=True)

    def __str__(self):
        return self.name


class Procedure(models.Model):
    code = models.CharField(max_length=20, unique=True)  # ex.: "PROC-LASER"
    name = models.CharField(max_length=120)              # "Laser de Alta Potência"
    category = models.ForeignKey(ProcedureCategory, on_delete=models.PROTECT)
    duration_estimate_min = models.PositiveSmallIntegerField(default=20)
    requires_image_guidance = models.BooleanField(default=False)  # US/fluoro
    price_brl = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))  # MVP

    def __str__(self):
        return f"{self.code} - {self.name}"

class Patient(models.Model):
    SEX_CHOICES = (("M", "Masculino"), ("F", "Feminino"), ("O", "Outro"))
    full_name = models.CharField(max_length=150)
    sex = models.CharField(max_length=1, choices=SEX_CHOICES)
    birth_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self): 
        return self.full_name


class Provider(models.Model):
    SPECIALTY_CHOICES = (
        ("Clínica Médica", "Clínica Médica"),
        ("Pediatria", "Pediatria"),
        ("Ginecologia", "Ginecologia"),
        ("Ortopedia", "Ortopedia"),
        ("Cardiologia", "Cardiologia"),
    )
    full_name = models.CharField(max_length=150)
    crm = models.CharField(max_length=30, blank=True)
    specialty = models.CharField(max_length=60, choices=SPECIALTY_CHOICES)

    def __str__(self): 
        return f"{self.full_name} ({self.specialty})"
class Appointment(models.Model):
    STATUS = (
        ("scheduled", "Agendada"),
        ("completed", "Concluída"),
        ("no_show", "Não compareceu"),
        ("cancelled", "Cancelada"),
    )
    patient = models.ForeignKey('Patient', on_delete=models.CASCADE)
    provider = models.ForeignKey('Provider', on_delete=models.PROTECT)
    scheduled_at = models.DateTimeField()
    status = models.CharField(max_length=12, choices=STATUS, default="scheduled")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["scheduled_at", "status"])]

    def __str__(self):
        return f"{self.patient} - {self.provider} @ {self.scheduled_at:%d/%m %H:%M}"


class Encounter(models.Model):
    appointment = models.OneToOneField(Appointment, null=True, blank=True, on_delete=models.SET_NULL)
    patient = models.ForeignKey('Patient', on_delete=models.CASCADE)
    provider = models.ForeignKey('Provider', on_delete=models.PROTECT)
    check_in = models.DateTimeField()
    check_out = models.DateTimeField(null=True, blank=True)
    reason = models.CharField(max_length=200, blank=True)
    diagnoses = models.ManyToManyField('Diagnosis', blank=True)
    procedures = models.ManyToManyField('Procedure', blank=True)


    @property
    def duration_minutes(self):
        if self.check_in and self.check_out:
            delta = self.check_out - self.check_in
            return int(delta.total_seconds() // 60)
        return None

    def __str__(self):
        return f"Atendimento de {self.patient} com {self.provider} em {self.check_in:%d/%m/%Y}"


class Vitals(models.Model):
    encounter = models.OneToOneField(Encounter, on_delete=models.CASCADE)
    height_cm = models.PositiveSmallIntegerField(null=True, blank=True)
    weight_kg = models.PositiveSmallIntegerField(null=True, blank=True)
    systolic = models.PositiveSmallIntegerField(null=True, blank=True)
    diastolic = models.PositiveSmallIntegerField(null=True, blank=True)
    heart_rate = models.PositiveSmallIntegerField(null=True, blank=True)

    def __str__(self):
        return f"Sinais vitais #{self.pk}"
