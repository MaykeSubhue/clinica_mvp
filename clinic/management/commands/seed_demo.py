from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker
import random
from datetime import date
from datetime import timedelta
from clinic.models import Patient, Provider, Diagnosis, Appointment, Encounter, Vitals, Procedure, ProcedureCategory
from clinic.models import (
    Patient, Provider, Diagnosis, Appointment, Encounter, Vitals,
    Procedure, ProcedureCategory,
    CarePlan, CareStep, PainAssessment,  # <-- NOVOS
)

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

        # Categorias de procedimento
        for model in (Procedure, ProcedureCategory):
            model.objects.all().delete()

        cat_laser = ProcedureCategory.objects.create(name="Laserterapia")
        cat_infil = ProcedureCategory.objects.create(name="Infiltrações")
        cat_blocks = ProcedureCategory.objects.create(name="Bloqueios (Simp./Neuroaxiais)")
        cat_rf = ProcedureCategory.objects.create(name="Radiofrequência")
        cat_eswt = ProcedureCategory.objects.create(name="Ondas de Choque (ESWT)")

        procedures = [
            # code, name, category, duration, image_guidance, price
            ("PROC-LASER", "Laser de Alta Potência", cat_laser, 25, False, 350.00),
            ("PROC-INFIL", "Infiltração Articular/Muscular", cat_infil, 30, True, 520.00),
            ("PROC-BLOQ", "Bloqueio Simpático/Neuroaxial", cat_blocks, 40, True, 980.00),
            ("PROC-RF", "Radiofrequência Convencional/Pulsada", cat_rf, 45, True, 1850.00),
            ("PROC-ESWT", "Ondas de Choque Extracorpóreas (ESWT)", cat_eswt, 20, False, 650.00),
        ]
        procedures = [Procedure.objects.create(
            code=c, name=n, category=cat, duration_estimate_min=dur, requires_image_guidance=img, price_brl=price
        ) for (c, n, cat, dur, img, price) in procedures]

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
                        # Atribui procedimentos de forma realista (maioria consultas sem procedimento, mas alguns têm)
                        roll = random.random()
                        if roll < 0.55:
                            # 55% apenas consulta clínica (sem procedimentos)
                            pass
                        elif roll < 0.85:
                            # 30% 1 procedimento
                            enc.procedures.add(random.choice(procedures))
                        else:
                            # 15% 2 procedimentos combinados (ex.: infiltração + laser ou RF sozinha)
                            enc.procedures.add(*random.sample(procedures, k=2))

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
    # mapeia os seus procedimentos criados acima
        proc_map = {
            "LASER": Procedure.objects.get(code="PROC-LASER"),
            "INFIL": Procedure.objects.get(code="PROC-INFIL"),
            "BLOCK": Procedure.objects.get(code="PROC-BLOQ"),
            "RF":    Procedure.objects.get(code="PROC-RF"),
            "ESWT":  Procedure.objects.get(code="PROC-ESWT"),
        }

        # efeito médio semanal por protocolo (queda em pontos na escala 0–10)
        weekly_effect = {
            "LASER": 0.25,  # resposta lenta e cumulativa
            "INFIL": 0.60,  # resposta mais rápida
            "BLOCK": 0.70,  # neuropática com boa resposta
            "RF":    0.80,  # grande queda pós-aplicação
            "ESWT":  0.35,  # progressiva
        }

        today = timezone.now().date()

        # pega uma amostra de pacientes (para não exagerar a base)
        amostra = random.sample(patients, k=min(120, len(patients)))

        for pt in amostra:
            proto = random.choice(list(proc_map.keys()))
            start = today - timedelta(days=random.randint(30, 120))

            plan = CarePlan.objects.create(
                patient=pt,
                diagnosis=random.choice([
                    "Lombalgia crônica", "Osteoartrite de joelho",
                    "Cervicalgia", "Dor miofascial"
                ]),
                protocol=proto,
                start_date=start,
                goal_pain_score=random.choice([2, 3, 4]),
            )

            # 3 a 5 etapas do procedimento do protocolo
            steps = random.randint(3, 5)
            for k in range(steps):
                step_date = start + timedelta(weeks=k)
                CareStep.objects.create(
                    care_plan=plan,
                    procedure=proc_map[proto],
                    scheduled_at=step_date,
                    done_at=step_date,
                    notes="Etapa planejada e realizada.",
                )

                # tenta vincular o procedimento a um encontro real daquele paciente na mesma data
                enc = (Encounter.objects
                    .filter(patient=pt,
                            check_out__date=step_date)  # precisa que check_out exista
                    .order_by('check_out')
                    .first())
                if enc:
                    enc.procedures.add(proc_map[proto])

            # linha do tempo da dor: 10–12 semanas
            baseline = random.randint(7, 10)
            current = baseline
            semanas = random.randint(10, 12)

            for w in range(semanas):
                drop = weekly_effect[proto] + random.uniform(-0.15, 0.15)
                drop = max(drop, 0)
                current = max(0, current - drop)

                PainAssessment.objects.create(
                    patient=pt,
                    recorded_at=start + timedelta(weeks=w),
                    score=round(current),
                    notes=f"Semana {w+1} • {proto}",
                )
