from datetime import date, datetime, time
from decimal import Decimal
from typing import Optional
from uuid import UUID

from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import NinjaAPI, Schema

from coop.models import CoopMember, Expense, Income, Job, TimeEntry

api = NinjaAPI(title="The Coop API", version="1.0.0")


# ── Schemas ──────────────────────────────────────────────────────────────


class JobOut(Schema):
    id: UUID
    name: str
    description: str
    is_active: bool


class JobIn(Schema):
    name: str
    description: str = ""


class TimeEntryIn(Schema):
    job_id: UUID
    date: date
    time_start: str  # "HH:MM" format
    time_end: str  # "HH:MM" format
    location: str = ""
    notes: str = ""
    # Admin-only: log this entry on behalf of another member
    member_id: Optional[UUID] = None


class TimeEntryOut(Schema):
    id: UUID
    member_name: str
    job_name: str
    date: date
    time_start: Optional[str] = None
    time_end: Optional[str] = None
    hours: Decimal
    location: str
    notes: str
    status: str
    approved_by_name: Optional[str] = None

    @staticmethod
    def resolve_time_start(obj):
        return obj.time_start.strftime("%H:%M") if obj.time_start else None

    @staticmethod
    def resolve_time_end(obj):
        return obj.time_end.strftime("%H:%M") if obj.time_end else None

    @staticmethod
    def resolve_member_name(obj):
        return str(obj.member)

    @staticmethod
    def resolve_job_name(obj):
        return obj.job.name

    @staticmethod
    def resolve_approved_by_name(obj):
        return str(obj.approved_by) if obj.approved_by else None


class IncomeIn(Schema):
    date: date
    amount: Decimal
    source: str
    notes: str = ""


class ExpenseIn(Schema):
    date: date
    amount: Decimal
    category: str
    notes: str = ""


class FinanceSummary(Schema):
    total_income: Decimal
    total_expenses: Decimal
    net_profit: Decimal


class MemberSplit(Schema):
    name: str
    hours: Decimal
    percentage: float
    cut: Decimal


# ── Helpers ──────────────────────────────────────────────────────────────


def _get_member(request) -> CoopMember:
    return CoopMember.objects.get(auth_user_id=request.auth_user.id)


# ── Health ───────────────────────────────────────────────────────────────


@api.get("/health/")
def health(request):
    return {"status": "ok"}


# ── Jobs ─────────────────────────────────────────────────────────────────


@api.get("/jobs/", response=list[JobOut])
def list_jobs(request):
    return Job.objects.filter(is_active=True)


@api.post("/jobs/", response=JobOut)
def create_job(request, data: JobIn):
    """
    Create a new job. Any authenticated member can create one — this lets
    people add jobs inline from the Log Hours form when they need to.

    Idempotent on name: if a job with the same name already exists (case-
    insensitive), return the existing one instead of erroring.
    """
    name = data.name.strip()
    if not name:
        return 400, {"detail": "Name is required"}

    existing = Job.objects.filter(name__iexact=name).first()
    if existing:
        if not existing.is_active:
            existing.is_active = True
            existing.save()
        return existing

    return Job.objects.create(name=name, description=data.description.strip())


# ── Time Entries ─────────────────────────────────────────────────────────


@api.post("/hours/", response={200: TimeEntryOut, 403: dict})
def create_time_entry(request, data: TimeEntryIn):
    actor = _get_member(request)
    job = get_object_or_404(Job, pk=data.job_id, is_active=True)

    # Determine whose entry this is. Admins may log on behalf of any member;
    # everyone else can only log for themselves.
    target_member = actor
    if data.member_id and data.member_id != actor.id:
        if actor.role != CoopMember.Role.ADMIN:
            return 403, {"detail": "Only admins can log hours for other members"}
        target_member = get_object_or_404(CoopMember, pk=data.member_id, is_active=True)

    # Minors logging for themselves go to pending. Anything an admin enters
    # (for self or another member) is auto-approved by the admin.
    status = TimeEntry.Status.PENDING
    approved_by = None
    approved_at = None
    if target_member.role != CoopMember.Role.MINOR or actor.role == CoopMember.Role.ADMIN:
        status = TimeEntry.Status.APPROVED
        approved_by = actor
        approved_at = timezone.now()

    t_start = datetime.strptime(data.time_start, "%H:%M").time()
    t_end = datetime.strptime(data.time_end, "%H:%M").time()

    entry = TimeEntry(
        member=target_member,
        job=job,
        date=data.date,
        time_start=t_start,
        time_end=t_end,
        hours=0,  # calculated in save()
        location=data.location,
        notes=data.notes,
        status=status,
        approved_by=approved_by,
        approved_at=approved_at,
    )
    entry.save()  # triggers hours calculation
    return entry


@api.get("/hours/", response=list[TimeEntryOut])
def list_time_entries(request, period: str = "week"):
    member = _get_member(request)
    today = date.today()
    from datetime import timedelta

    if period == "month":
        start = today.replace(day=1)
    elif period == "year":
        start = today.replace(month=1, day=1)
    else:
        start = today - timedelta(days=today.weekday())

    return TimeEntry.objects.filter(
        member=member, date__gte=start
    ).select_related("job", "approved_by", "member")


# ── Finances ─────────────────────────────────────────────────────────────


@api.post("/income/")
def create_income(request, data: IncomeIn):
    member = _get_member(request)
    Income.objects.create(
        date=data.date,
        amount=data.amount,
        source=data.source,
        notes=data.notes,
        recorded_by=member,
    )
    return {"ok": True}


@api.post("/expenses/")
def create_expense(request, data: ExpenseIn):
    member = _get_member(request)
    Expense.objects.create(
        date=data.date,
        amount=data.amount,
        category=data.category,
        notes=data.notes,
        recorded_by=member,
    )
    return {"ok": True}


@api.get("/finances/summary/", response=FinanceSummary)
def finance_summary(request):
    today = date.today()
    year_start = today.replace(month=1, day=1)

    total_income = (
        Income.objects.filter(date__gte=year_start).aggregate(t=Sum("amount"))["t"]
        or Decimal("0")
    )
    total_expenses = (
        Expense.objects.filter(date__gte=year_start).aggregate(t=Sum("amount"))["t"]
        or Decimal("0")
    )
    return {
        "total_income": total_income,
        "total_expenses": total_expenses,
        "net_profit": total_income - total_expenses,
    }


@api.get("/finances/splits/", response=list[MemberSplit])
def member_splits(request):
    today = date.today()
    year_start = today.replace(month=1, day=1)

    total_income = (
        Income.objects.filter(date__gte=year_start).aggregate(t=Sum("amount"))["t"]
        or Decimal("0")
    )
    total_expenses = (
        Expense.objects.filter(date__gte=year_start).aggregate(t=Sum("amount"))["t"]
        or Decimal("0")
    )
    net_profit = total_income - total_expenses

    members_hours = (
        TimeEntry.objects.filter(
            date__gte=year_start,
            status=TimeEntry.Status.APPROVED,
        )
        .values("member__display_name")
        .annotate(total_hours=Sum("hours"))
        .order_by("-total_hours")
    )
    grand_total = sum(m["total_hours"] for m in members_hours)

    splits = []
    for m in members_hours:
        pct = float(round(m["total_hours"] / grand_total * 100, 1)) if grand_total else 0
        cut = (
            round(net_profit * m["total_hours"] / grand_total, 2)
            if grand_total
            else Decimal("0")
        )
        splits.append(
            {
                "name": m["member__display_name"],
                "hours": m["total_hours"],
                "percentage": pct,
                "cut": cut,
            }
        )
    return splits
