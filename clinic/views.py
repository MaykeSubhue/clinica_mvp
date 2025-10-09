from django.contrib.admin.views.decorators import staff_member_required
from datetime import timedelta, datetime
import json
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.shortcuts import render
from django.utils import timezone
from .models import Appointment, Encounter, Provider, Diagnosis
import csv
from django.http import HttpResponse
from django.utils.dateparse import parse_date

@staff_member_required
def dashboard(request):
    # filtros
    days_default = 30
    days = int(request.GET.get("days", days_default))
    start = request.GET.get("start")
    end = request.GET.get("end")
    status = request.GET.get("status")  # completed, no_show, cancelled, scheduled
    provider_id = request.GET.get("provider")

    # período: se vier start/end usa, senão usa "days"
    if start and end:
        since = timezone.make_aware(datetime.combine(parse_date(start), datetime.min.time()))
        until = timezone.make_aware(datetime.combine(parse_date(end), datetime.max.time()))
    else:
        since = timezone.now() - timedelta(days=days)
        until = timezone.now()

    appts = Appointment.objects.filter(scheduled_at__range=(since, until))

    if status:
        appts = appts.filter(status=status)

    if provider_id:
        appts = appts.filter(provider_id=provider_id)

    # métricas
    total = appts.count()
    completed = appts.filter(status="completed").count()
    no_show = appts.filter(status="no_show").count()
    cancelled = appts.filter(status="cancelled").count()

    completion_rate = round((completed / total * 100), 1) if total else 0
    no_show_rate = round((no_show / total * 100), 1) if total else 0

    encs = Encounter.objects.filter(appointment__in=appts, check_out__isnull=False)
    durations = [e.duration_minutes for e in encs if e.duration_minutes is not None]
    avg_minutes = round(sum(durations)/len(durations), 1) if durations else 0

    daily_qs = (appts.annotate(day=TruncDate("scheduled_at"))
                .values("day").annotate(cnt=Count("id")).order_by("day"))
    daily = [{"day": d["day"].strftime("%Y-%m-%d"), "cnt": d["cnt"]} for d in daily_qs]

    by_spec_qs = (appts.values("provider__specialty")
                  .annotate(cnt=Count("id")).order_by("-cnt"))
    by_spec = [{"spec": r["provider__specialty"], "cnt": r["cnt"]} for r in by_spec_qs]

    top_dx_qs = (Diagnosis.objects
                 .filter(encounter__appointment__in=appts, encounter__check_out__isnull=False)
                 .values("code", "description").annotate(cnt=Count("id")).order_by("-cnt")[:10])
    top_dx = [{"label": f'{r["code"]}', "cnt": r["cnt"]} for r in top_dx_qs]

    specialties = list(Provider.objects.values_list("specialty", flat=True).distinct())
    providers = Provider.objects.order_by("full_name").values("id", "full_name")

    ctx = dict(
        total=total, completed=completed, cancelled=cancelled, no_show=no_show,
        completion_rate=completion_rate, no_show_rate=no_show_rate, avg_minutes=avg_minutes,
        days=days,  # ainda mostramos p/ fallback
        start=start or "", end=end or "", status=status or "", provider_id=provider_id or "",
        specialties=specialties, providers=list(providers),
        daily_json=json.dumps(daily), by_spec_json=json.dumps(by_spec), top_dx_json=json.dumps(top_dx),
    )

    return render(request, "clinic/dashboard.html", ctx)

@staff_member_required
def export_appointments_csv(request):
    # reaproveita os mesmos filtros da dashboard
    days = int(request.GET.get("days", 30))
    start = request.GET.get("start")
    end = request.GET.get("end")
    status = request.GET.get("status")
    provider_id = request.GET.get("provider")

    if start and end:
        since = timezone.make_aware(datetime.combine(parse_date(start), datetime.min.time()))
        until = timezone.make_aware(datetime.combine(parse_date(end), datetime.max.time()))
    else:
        since = timezone.now() - timedelta(days=days)
        until = timezone.now()

    qs = Appointment.objects.select_related("patient", "provider").filter(
        scheduled_at__range=(since, until)
    )
    if status:
        qs = qs.filter(status=status)
    if provider_id:
        qs = qs.filter(provider_id=provider_id)

    # resposta CSV
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="appointments.csv"'
    writer = csv.writer(response)
    writer.writerow(["Data/Hora", "Paciente", "Sexo", "Nasc", "Médico", "Especialidade", "Status"])

    for a in qs.order_by("-scheduled_at"):
        writer.writerow([
            a.scheduled_at.strftime("%Y-%m-%d %H:%M"),
            a.patient.full_name,
            a.patient.sex,
            a.patient.birth_date.strftime("%Y-%m-%d") if a.patient.birth_date else "",
            a.provider.full_name,
            a.provider.specialty,
            a.get_status_display(),
        ])

    return response