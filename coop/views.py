from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Q, Sum
from django.http import HttpRequest
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .decorators import require_role
from .models import CoopMember, Expense, Income, Job, TimeEntry, WoodInventory


def _get_or_create_member(request: HttpRequest) -> CoopMember:
    """Get or auto-create a CoopMember from the authenticated auth_user."""
    member, _ = CoopMember.objects.get_or_create(
        auth_user_id=request.auth_user.id,
        defaults={
            "username": request.auth_user.username,
            "display_name": request.auth_user.username,
        },
    )
    return member


def dashboard(request: HttpRequest):
    member = _get_or_create_member(request)

    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    my_hours = (
        TimeEntry.objects.filter(
            member=member,
            date__gte=week_start,
            date__lte=week_end,
            status=TimeEntry.Status.APPROVED,
        ).aggregate(total=Sum("hours"))["total"]
        or Decimal("0")
    )

    team_hours = (
        TimeEntry.objects.filter(
            date__gte=week_start,
            date__lte=week_end,
            status=TimeEntry.Status.APPROVED,
        ).aggregate(total=Sum("hours"))["total"]
        or Decimal("0")
    )

    # Pending approvals — admins see all, others see their dependents
    if member.role == CoopMember.Role.ADMIN:
        pending_count = TimeEntry.objects.filter(
            status=TimeEntry.Status.PENDING,
        ).count()
    else:
        pending_count = TimeEntry.objects.filter(
            status=TimeEntry.Status.PENDING,
            member__approver=member,
        ).count()

    year_start = today.replace(month=1, day=1)
    total_income = (
        Income.objects.filter(date__gte=year_start).aggregate(total=Sum("amount"))[
            "total"
        ]
        or Decimal("0")
    )
    total_expenses = (
        Expense.objects.filter(date__gte=year_start).aggregate(total=Sum("amount"))[
            "total"
        ]
        or Decimal("0")
    )
    net_profit = total_income - total_expenses

    # Calculate this member's projected cut
    ytd_my_hours = (
        TimeEntry.objects.filter(
            member=member,
            date__gte=year_start,
            status=TimeEntry.Status.APPROVED,
        ).aggregate(total=Sum("hours"))["total"]
        or Decimal("0")
    )
    ytd_team_hours = (
        TimeEntry.objects.filter(
            date__gte=year_start,
            status=TimeEntry.Status.APPROVED,
        ).aggregate(total=Sum("hours"))["total"]
        or Decimal("0")
    )
    my_cut = (
        round(net_profit * ytd_my_hours / ytd_team_hours, 2)
        if ytd_team_hours > 0
        else Decimal("0")
    )

    recent_entries = TimeEntry.objects.filter(member=member).select_related("job")[:10]

    context = {
        "member": member,
        "my_hours": my_hours,
        "team_hours": team_hours,
        "my_percentage": (
            round(my_hours / team_hours * 100, 1) if team_hours > 0 else Decimal("0")
        ),
        "my_cut": my_cut,
        "pending_count": pending_count,
        "total_income": total_income,
        "total_expenses": total_expenses,
        "net_profit": net_profit,
        "recent_entries": recent_entries,
        "week_start": week_start,
        "week_end": week_end,
    }
    return render(request, "coop/dashboard.html", context)


def hours_list(request: HttpRequest):
    member = _get_or_create_member(request)
    period = request.GET.get("period", "week")
    today = date.today()

    if period == "week":
        start = today - timedelta(days=today.weekday())
    elif period == "month":
        start = today.replace(day=1)
    elif period == "year":
        start = today.replace(month=1, day=1)
    else:
        start = today - timedelta(days=today.weekday())

    entries = TimeEntry.objects.filter(
        member=member, date__gte=start
    ).select_related("job", "approved_by")

    total = entries.filter(status=TimeEntry.Status.APPROVED).aggregate(
        total=Sum("hours")
    )["total"] or Decimal("0")

    context = {
        "entries": entries,
        "total_hours": total,
        "period": period,
    }

    if request.headers.get("HX-Request"):
        return render(request, "partials/hours_table.html", context)
    return render(request, "coop/hours.html", context)


@require_role("admin")
def team_hours(request: HttpRequest):
    """Admin view — all members' time entries."""
    member = _get_or_create_member(request)
    period = request.GET.get("period", "week")
    filter_member = request.GET.get("member", "")
    filter_job = request.GET.get("job", "")
    today = date.today()

    if period == "week":
        start = today - timedelta(days=today.weekday())
    elif period == "month":
        start = today.replace(day=1)
    elif period == "year":
        start = today.replace(month=1, day=1)
    else:
        start = today - timedelta(days=today.weekday())

    entries = TimeEntry.objects.filter(date__gte=start).select_related(
        "member", "job", "approved_by"
    )

    if filter_member:
        entries = entries.filter(member__id=filter_member)
    if filter_job:
        entries = entries.filter(job__id=filter_job)

    total = entries.filter(status=TimeEntry.Status.APPROVED).aggregate(
        total=Sum("hours")
    )["total"] or Decimal("0")

    # Per-member subtotals
    member_totals = (
        entries.filter(status=TimeEntry.Status.APPROVED)
        .values("member__display_name")
        .annotate(total_hours=Sum("hours"))
        .order_by("-total_hours")
    )

    context = {
        "member": member,
        "entries": entries,
        "total_hours": total,
        "member_totals": member_totals,
        "period": period,
        "filter_member": filter_member,
        "filter_job": filter_job,
        "all_members": CoopMember.objects.filter(is_active=True),
        "all_jobs": Job.objects.filter(is_active=True),
    }

    if request.headers.get("HX-Request"):
        return render(request, "partials/team_hours_table.html", context)
    return render(request, "coop/team_hours.html", context)


def approval_queue(request: HttpRequest):
    member = _get_or_create_member(request)

    # Admins see all pending, others see only their dependents
    if member.role == CoopMember.Role.ADMIN:
        pending = TimeEntry.objects.filter(
            status=TimeEntry.Status.PENDING,
        ).select_related("member", "job")
    else:
        pending = TimeEntry.objects.filter(
            status=TimeEntry.Status.PENDING,
            member__approver=member,
        ).select_related("member", "job")

    context = {"pending_entries": pending, "member": member}
    return render(request, "coop/approvals.html", context)


def approve_entry(request: HttpRequest, entry_id):
    member = _get_or_create_member(request)

    # Admins can approve any entry, others only their dependents
    if member.role == CoopMember.Role.ADMIN:
        entry = get_object_or_404(
            TimeEntry, pk=entry_id, status=TimeEntry.Status.PENDING
        )
    else:
        entry = get_object_or_404(
            TimeEntry,
            pk=entry_id,
            member__approver=member,
            status=TimeEntry.Status.PENDING,
        )

    entry.status = TimeEntry.Status.APPROVED
    entry.approved_by = member
    entry.approved_at = timezone.now()
    entry.save()

    if request.headers.get("HX-Request"):
        return render(request, "partials/approval_row.html", {"entry": entry})
    return render(request, "coop/approvals.html")


def reject_entry(request: HttpRequest, entry_id):
    member = _get_or_create_member(request)

    if member.role == CoopMember.Role.ADMIN:
        entry = get_object_or_404(
            TimeEntry, pk=entry_id, status=TimeEntry.Status.PENDING
        )
    else:
        entry = get_object_or_404(
            TimeEntry,
            pk=entry_id,
            member__approver=member,
            status=TimeEntry.Status.PENDING,
        )

    entry.status = TimeEntry.Status.REJECTED
    entry.approved_by = member
    entry.approved_at = timezone.now()
    entry.save()

    if request.headers.get("HX-Request"):
        return render(request, "partials/approval_row.html", {"entry": entry})
    return render(request, "coop/approvals.html")


@require_role("admin")
def finances(request: HttpRequest):
    member = _get_or_create_member(request)
    today = date.today()
    year_start = today.replace(month=1, day=1)

    income_list = Income.objects.filter(date__gte=year_start).select_related(
        "recorded_by"
    )
    expense_list = Expense.objects.filter(date__gte=year_start).select_related(
        "recorded_by"
    )

    total_income = income_list.aggregate(total=Sum("amount"))["total"] or Decimal("0")
    total_expenses = expense_list.aggregate(total=Sum("amount"))["total"] or Decimal(
        "0"
    )

    members_hours = (
        TimeEntry.objects.filter(
            date__gte=year_start,
            status=TimeEntry.Status.APPROVED,
        )
        .values("member__id", "member__display_name")
        .annotate(total_hours=Sum("hours"))
        .order_by("-total_hours")
    )
    grand_total_hours = sum(m["total_hours"] for m in members_hours)
    net_profit = total_income - total_expenses

    splits = []
    for m in members_hours:
        pct = (
            round(m["total_hours"] / grand_total_hours * 100, 1)
            if grand_total_hours > 0
            else 0
        )
        splits.append(
            {
                "name": m["member__display_name"],
                "hours": m["total_hours"],
                "percentage": pct,
                "cut": round(net_profit * m["total_hours"] / grand_total_hours, 2)
                if grand_total_hours > 0
                else Decimal("0"),
            }
        )

    context = {
        "member": member,
        "income_list": income_list,
        "expense_list": expense_list,
        "total_income": total_income,
        "total_expenses": total_expenses,
        "net_profit": net_profit,
        "splits": splits,
    }
    return render(request, "coop/finances.html", context)


def log_hours(request: HttpRequest):
    member = _get_or_create_member(request)
    jobs = Job.objects.filter(is_active=True)
    context = {"member": member, "jobs": jobs}
    return render(request, "coop/log_hours.html", context)


def inventory(request: HttpRequest):
    member = _get_or_create_member(request)
    filter_status = request.GET.get("status", "")

    items = WoodInventory.objects.select_related("recorded_by")
    if filter_status:
        items = items.filter(status=filter_status)

    # Summary totals
    available = (
        WoodInventory.objects.filter(status=WoodInventory.Status.AVAILABLE)
        .aggregate(total=Sum("quantity"))["total"]
        or Decimal("0")
    )
    spoken_for = (
        WoodInventory.objects.filter(status=WoodInventory.Status.SPOKEN_FOR)
        .aggregate(total=Sum("quantity"))["total"]
        or Decimal("0")
    )
    today = date.today()
    year_start = today.replace(month=1, day=1)
    sold_ytd = (
        WoodInventory.objects.filter(
            status=WoodInventory.Status.SOLD, date_sold__gte=year_start
        )
        .aggregate(total=Sum("quantity"))["total"]
        or Decimal("0")
    )

    context = {
        "member": member,
        "items": items,
        "available": available,
        "spoken_for": spoken_for,
        "sold_ytd": sold_ytd,
        "filter_status": filter_status,
    }

    if request.headers.get("HX-Request"):
        return render(request, "partials/inventory_table.html", context)
    return render(request, "coop/inventory.html", context)
