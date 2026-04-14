import uuid

from django.db import models


class CoopMember(models.Model):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        MEMBER = "member", "Member"
        MINOR = "minor", "Minor"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Links to noegos-auth user by their auth user_id (from JWT sub claim)
    auth_user_id = models.UUIDField(unique=True)
    username = models.CharField(max_length=150, unique=True)
    display_name = models.CharField(max_length=255)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)
    approver = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dependents",
        help_text="Required for minors — the adult who approves their work",
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.display_name or self.username

    class Meta:
        ordering = ["display_name"]


class Job(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    rate_multiplier = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=1.00,
        help_text="Future use — weight certain jobs differently",
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class TimeEntry(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(
        CoopMember, on_delete=models.CASCADE, related_name="time_entries"
    )
    job = models.ForeignKey(Job, on_delete=models.PROTECT, related_name="time_entries")
    date = models.DateField()
    time_start = models.TimeField(help_text="When work started", null=True, blank=True)
    time_end = models.TimeField(help_text="When work ended", null=True, blank=True)
    hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Auto-calculated from start/end times",
    )
    location = models.CharField(
        max_length=255,
        blank=True,
        help_text="Where the work was done — north ridge, creek lot, etc.",
    )
    notes = models.TextField(blank=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    approved_by = models.ForeignKey(
        CoopMember,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_entries",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.time_start and self.time_end:
            from datetime import datetime, timedelta
            from decimal import Decimal

            start = datetime.combine(self.date, self.time_start)
            end = datetime.combine(self.date, self.time_end)
            if end <= start:
                end += timedelta(days=1)  # handle overnight
            diff = (end - start).total_seconds() / 3600
            self.hours = Decimal(str(round(diff, 2)))
        super().save(*args, **kwargs)

    @property
    def time_display(self):
        if self.time_start and self.time_end:
            return f"{self.time_start.strftime('%I:%M %p')} – {self.time_end.strftime('%I:%M %p')}"
        return ""

    def __str__(self):
        return f"{self.member} - {self.job} - {self.date} ({self.hours}h)"

    class Meta:
        ordering = ["-date", "-created_at"]
        verbose_name_plural = "time entries"


class Income(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    source = models.CharField(max_length=255, help_text="Who bought the wood, etc.")
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        CoopMember, on_delete=models.PROTECT, related_name="recorded_income"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"${self.amount} from {self.source} on {self.date}"

    class Meta:
        ordering = ["-date"]
        verbose_name_plural = "income"


class WoodInventory(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        SPOKEN_FOR = "spoken_for", "Spoken For"
        SOLD = "sold", "Sold"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wood_type = models.CharField(max_length=100, help_text="Oak, Walnut, Mixed Hardwood, etc.")
    quantity = models.DecimalField(
        max_digits=6, decimal_places=2, help_text="Quantity in cords"
    )
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.AVAILABLE
    )
    buyer = models.CharField(
        max_length=255, blank=True, help_text="Who it's spoken for or sold to"
    )
    location = models.CharField(
        max_length=255, blank=True, help_text="South rack, drying shed, etc."
    )
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        CoopMember, on_delete=models.PROTECT, related_name="recorded_inventory"
    )
    date_added = models.DateField()
    date_sold = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.quantity} cords {self.wood_type} ({self.get_status_display()})"

    class Meta:
        ordering = ["-date_added"]
        verbose_name_plural = "wood inventory"


class Expense(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(
        max_length=255, help_text="Fuel, equipment, supplies, etc."
    )
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        CoopMember, on_delete=models.PROTECT, related_name="recorded_expenses"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"${self.amount} for {self.category} on {self.date}"

    class Meta:
        ordering = ["-date"]
