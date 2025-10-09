from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker
import random
from datetime import timedelta
from clinic.models import Patient, Provider, Diagnosis, Appointment, Encounter, Vitals

class Command(BaseCommand):
    help = "Gera dados fake para demo da clínica"

    def handle(self, *args, **kwargs):
        fake = Faker("pt_BR")
        random.seed(42)

        # Limpa tabelas (MVP)
        Vitals.objects.all().delete()
        Encounter.objects.all().delete()
        Appointment.objects.all().delete()
        Diagnosis.objects.all().delete()
        Provider.objects.all().delete()
        Patient.objects.all().delete()

        # Providers
        specialties = ["Clínica Médica", "Pediatria", "Ginecologia", "Ortopedia", "Cardiologia"]
        providers = []
        for s in specialties:
            for _ in range(3):
                providers.append(Provider.objects.create(
                    full_name=fake.name(),
                    crm=str(fake.random_number(digits=6)),
                    specialty=s
                ))

        # Diagnósticos (pseudo-CID)
        diag_pool = [
            ("J06.9", "IVAS não especificada"),
            ("I10", "Hipertensão essencial"),
            ("E11.9", "DM2 sem complicações"),
            ("M54.5", "Dor lombar"),
            ("Z00.0", "Exame de rotina"),
            ("N39.0", "ITU"),
            ("J45.9", "Asma"),
            ("K21.9", "DRGE"),
        ]
        diagnoses = [Diagnosis.objects.create(code=c, description=d) for c, d in diag_pool]

        # Pacientes
        patients = []
        for _ in range(500):
            sex = random.choice(["M", "F"])
            patients.append(Patient.objects.create(
                full_name=fake.name_male() if sex == "M" else fake.name_female(),
                sex=sex,
                birth_date=fake.date_of_birth(minimum_age=0, maximum_age=95),
            ))

        # Agenda: últimos 90 dias + próximos 7
        start = timezone.now() - timedelta(days=90)
        end = timezone.now() + timedelta(days=7)
        day = start
        total_appts = 0

        while day <= end:
            for prov in providers:
                slots = random.randint(6, 12)  # consultas/dia por profissional
                for i in range(slots):
                    sched = (day.replace(hour=8, minute=0, second=0, microsecond=0)
                             + timedelta(minutes=i * (480 // slots)))

                    # menos agenda fim de semana
                    if sched.weekday() >= 5 and random.random() < 0.7:
                        continue

                    appt = Appointment.objects.create(
                        patient=random.choice(patients),
                        provider=prov,
                        scheduled_at=sched,
                        status="scheduled"
                    )
                    total_appts += 1

                    r = random.random()
                    if r < 0.15:
                        appt.status = "no_show"
                    elif r < 0.20:
                        appt.status = "cancelled"
                    else:
                        appt.status = "completed"
                        # Encounter
                        check_in_offset = random.randint(-10, 20)
                        duration = random.randint(12, 35)
                        enc = Encounter.objects.create(
                            appointment=appt,
                            patient=appt.patient,
                            provider=appt.provider,
                            check_in=appt.scheduled_at + timedelta(minutes=check_in_offset),
                            check_out=appt.scheduled_at + timedelta(minutes=check_in_offset + duration),
                            reason=random.choice(["Rotina", "Dor", "Retorno", "Resultado de exame"]),
                        )
                        enc.diagnoses.add(*random.sample(diagnoses, k=random.choice([1,1,2])))
                        Vitals.objects.create(
                            encounter=enc,
                            height_cm=random.randint(150, 185),
                            weight_kg=random.randint(50, 110),
                            systolic=random.randint(105, 150),
                            diastolic=random.randint(65, 95),
                            heart_rate=random.randint(55, 105),
                        )
                    appt.save()
            day += timedelta(days=1)

        self.stdout.write(self.style.SUCCESS(
            f"Seed OK: {len(patients)} pacientes, {len(providers)} profissionais, {total_appts} consultas."
        ))
