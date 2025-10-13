from django.contrib.admin.views.decorators import staff_member_required
from datetime import timedelta, datetime, time
import json
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.shortcuts import render
from django.utils import timezone
from .models import Appointment, Encounter, Provider, Diagnosis, Procedure
from django.db.models import Sum
import csv
from django.http import HttpResponse
from django.utils.dateparse import parse_date
from django.contrib.auth.models import User
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from .forms import StaffSignupForm
from django.shortcuts import render, redirect

@staff_member_required
def dashboard(request):
    # --- filtros ---
    days = int(request.GET.get("days", 30))        # fallback quando não há start/end
    status = request.GET.get("status") or ""       # completed, no_show, cancelled, scheduled
    provider_id = request.GET.get("provider") or ""

    start_str = request.GET.get("start") or ""
    end_str = request.GET.get("end") or ""

    start_date = parse_date(start_str) if start_str else None
    end_date = parse_date(end_str) if end_str else None

    # período: se vier start/end válidos usa; senão usa "days"
    if start_date and end_date:
        since = timezone.make_aware(datetime.combine(start_date, time.min))
        until = timezone.make_aware(datetime.combine(end_date, time.max))
    else:
        since = timezone.now() - timedelta(days=days)
        until = timezone.now()

    appts = Appointment.objects.filter(scheduled_at__range=(since, until))
    if status:
        appts = appts.filter(status=status)
    if provider_id:
        appts = appts.filter(provider_id=provider_id)

    # --- métricas principais ---
    total = appts.count()
    completed = appts.filter(status="completed").count()
    no_show = appts.filter(status="no_show").count()
    cancelled = appts.filter(status="cancelled").count()

    completion_rate = round((completed / total * 100), 1) if total else 0
    no_show_rate = round((no_show / total * 100), 1) if total else 0

    encs = Encounter.objects.filter(appointment__in=appts, check_out__isnull=False)
    durations = [e.duration_minutes for e in encs if e.duration_minutes is not None]
    avg_minutes = round(sum(durations)/len(durations), 1) if durations else 0

    # séries e agregações
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

    # procedimentos + receita estimada (MVP)
    proc_qs = (Procedure.objects
        .filter(encounter__appointment__in=appts, encounter__check_out__isnull=False)
        .values("name", "category__name")
        .annotate(qtd=Count("id"))
        .order_by("-qtd"))
    procedures_data = [{"label": r["name"], "cnt": r["qtd"], "cat": r["category__name"]} for r in proc_qs]

    proc_revenue_qs = (Encounter.objects
        .filter(appointment__in=appts, check_out__isnull=False, procedures__isnull=False)
        .values("procedures__id")
        .annotate(subtotal=Sum("procedures__price_brl")))
    revenue_total = float(sum(row["subtotal"] or 0 for row in proc_revenue_qs))

    # auxiliares
    specialties = list(Provider.objects.values_list("specialty", flat=True).distinct())
    providers = Provider.objects.order_by("full_name").values("id", "full_name")

    # contexto
    ctx = dict(
        total=total, completed=completed, cancelled=cancelled, no_show=no_show,
        completion_rate=completion_rate, no_show_rate=no_show_rate, avg_minutes=avg_minutes,
        days=days, start=start_str, end=end_str, status=status, provider_id=str(provider_id),
        specialties=specialties, providers=list(providers),
        daily_json=json.dumps(daily), by_spec_json=json.dumps(by_spec), top_dx_json=json.dumps(top_dx),
        procedures_json=json.dumps(procedures_data), revenue_total=round(revenue_total, 2),
    )
    ctx["now"] = timezone.now() #type: ignore
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
        since = timezone.make_aware(datetime.combine(parse_date(start), datetime.min.time())) # type: ignore
        until = timezone.make_aware(datetime.combine(parse_date(end), datetime.max.time())) # type: ignore
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
    writer.writerow(["Data/Hora", "Paciente", "Sexo", "Nasc", "Médico", "Especialidade", "Status", "Procedimentos"])

# @user_passes_test(lambda u: u.is_superuser)  # só superuser pode cadastrar
# def staff_new(request):
#     if request.method == "POST":
#         form = StaffForm(request.POST)
#         if form.is_valid():
#             user = form.save(commit=False)
#             user.is_active = True
#             user.is_staff = True
#             user.set_password(form.cleaned_data["password"])
#             user.save()
#             messages.success(request, f"Funcionário '{user.username}' criado com sucesso.")
#             return redirect("dashboard")
#         else:
#             messages.error(request, "Corrija os campos indicados.")
#     else:
#         form = StaffForm()

#     return render(request, "clinic/staff_new.html", {"form": form})



def staff_signup(request):
    if request.method == "POST":
        form = StaffSignupForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Conta criada! Você já pode fazer login.")
            return redirect("login")
        else:
            messages.error(request, "Corrija os campos destacados.")
    else:
        form = StaffSignupForm()

    return render(request, "registration/signup.html", {"form": form})



