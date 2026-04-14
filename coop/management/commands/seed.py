import uuid
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from coop.models import CoopMember, Expense, Income, Job, TimeEntry, WoodInventory


class Command(BaseCommand):
    help = "Seed the database with sample co-op data"

    def handle(self, *args, **options):
        # Jobs
        jobs = {}
        for name, desc in [
            ("Wood Cutting", "Felling and bucking trees"),
            ("Splitting", "Splitting rounds into firewood"),
            ("Stacking", "Stacking split wood for seasoning"),
            ("Hauling", "Transporting wood to buyers"),
            ("Equipment Maintenance", "Chainsaw sharpening, truck maintenance"),
        ]:
            jobs[name], _ = Job.objects.get_or_create(name=name, defaults={"description": desc})
        self.stdout.write(f"  Created {len(jobs)} jobs")

        # Members — get or create the dev user first
        travis, _ = CoopMember.objects.get_or_create(
            auth_user_id=uuid.UUID(int=1),
            defaults={"username": "dev", "display_name": "Travis", "role": "admin"},
        )
        # Ensure dev user is admin with correct display name
        changed = False
        if travis.display_name in ("dev", "Dev User"):
            travis.display_name = "Travis"
            changed = True
        if travis.role != "admin":
            travis.role = "admin"
            changed = True
        if changed:
            travis.save()

        mike, _ = CoopMember.objects.get_or_create(
            auth_user_id=uuid.UUID(int=2),
            defaults={"username": "mike", "display_name": "Mike", "role": "member"},
        )
        sarah, _ = CoopMember.objects.get_or_create(
            auth_user_id=uuid.UUID(int=3),
            defaults={"username": "sarah", "display_name": "Sarah", "role": "member"},
        )
        jake, _ = CoopMember.objects.get_or_create(
            auth_user_id=uuid.UUID(int=4),
            defaults={
                "username": "jake",
                "display_name": "Jake",
                "role": "minor",
                "approver": travis,
            },
        )
        emma, _ = CoopMember.objects.get_or_create(
            auth_user_id=uuid.UUID(int=5),
            defaults={
                "username": "emma",
                "display_name": "Emma",
                "role": "minor",
                "approver": mike,
            },
        )
        self.stdout.write(f"  Created 5 members (2 minors)")

        today = date.today()
        monday = today - timedelta(days=today.weekday())

        # Time entries for this week and last few weeks
        entries_data = [
            # This week — Travis
            (travis, "Wood Cutting", monday, "5.00", "approved", "Cleared the oak by the creek"),
            (travis, "Splitting", monday + timedelta(1), "3.50", "approved", "Split yesterday's haul"),
            (travis, "Hauling", monday + timedelta(2), "2.00", "approved", "Delivered to Petersons"),
            (travis, "Wood Cutting", monday + timedelta(3), "4.00", "approved", "Walnut stand on north side"),
            # This week — Mike
            (mike, "Wood Cutting", monday, "6.00", "approved", "East ridge clearing"),
            (mike, "Splitting", monday + timedelta(1), "4.00", "approved", ""),
            (mike, "Equipment Maintenance", monday + timedelta(2), "2.00", "approved", "Sharpened all chains"),
            # This week — Sarah
            (sarah, "Stacking", monday, "3.00", "approved", "Organized the south rack"),
            (sarah, "Stacking", monday + timedelta(1), "4.00", "approved", ""),
            (sarah, "Hauling", monday + timedelta(3), "3.00", "approved", "Delivery to Millers"),
            # This week — Jake (minor, some pending)
            (jake, "Stacking", monday, "2.00", "approved", "Helped dad stack"),
            (jake, "Stacking", monday + timedelta(2), "1.50", "pending", "After school"),
            (jake, "Splitting", monday + timedelta(3), "2.00", "pending", "Used the small maul"),
            # This week — Emma (minor, pending)
            (emma, "Stacking", monday + timedelta(1), "1.50", "pending", "Weekend help"),
            # Last week
            (travis, "Wood Cutting", monday - timedelta(7), "6.00", "approved", ""),
            (travis, "Splitting", monday - timedelta(6), "4.00", "approved", ""),
            (mike, "Wood Cutting", monday - timedelta(7), "5.00", "approved", ""),
            (mike, "Hauling", monday - timedelta(5), "3.00", "approved", "Big delivery"),
            (sarah, "Stacking", monday - timedelta(7), "4.00", "approved", ""),
            (sarah, "Hauling", monday - timedelta(4), "2.50", "approved", ""),
            (jake, "Stacking", monday - timedelta(6), "2.00", "approved", ""),
            # Two weeks ago
            (travis, "Wood Cutting", monday - timedelta(14), "5.00", "approved", ""),
            (mike, "Splitting", monday - timedelta(14), "6.00", "approved", ""),
            (sarah, "Equipment Maintenance", monday - timedelta(13), "1.50", "approved", "Oil change on truck"),
        ]

        created = 0
        for member, job_name, entry_date, hours, status, notes in entries_data:
            _, was_created = TimeEntry.objects.get_or_create(
                member=member,
                job=jobs[job_name],
                date=entry_date,
                defaults={
                    "hours": Decimal(hours),
                    "status": status,
                    "notes": notes,
                    "approved_by": travis if status == "approved" else None,
                    "approved_at": timezone.now() if status == "approved" else None,
                },
            )
            if was_created:
                created += 1
        self.stdout.write(f"  Created {created} time entries")

        # Income — wood sales this year
        income_data = [
            (today - timedelta(60), "800.00", "Peterson family", "2 cords seasoned oak"),
            (today - timedelta(45), "450.00", "Miller farm", "1 cord mixed hardwood"),
            (today - timedelta(30), "1200.00", "Johnson estate", "3 cords oak and walnut"),
            (today - timedelta(14), "600.00", "Riverside Campground", "Campfire bundles"),
            (today - timedelta(3), "550.00", "Peterson family", "Follow-up order"),
        ]
        for inc_date, amount, source, notes in income_data:
            Income.objects.get_or_create(
                date=inc_date,
                source=source,
                defaults={
                    "amount": Decimal(amount),
                    "notes": notes,
                    "recorded_by": travis,
                },
            )
        self.stdout.write(f"  Created {len(income_data)} income records")

        # Expenses
        expense_data = [
            (today - timedelta(55), "85.00", "Fuel", "Gas for truck and chainsaws"),
            (today - timedelta(40), "120.00", "Equipment", "New chain for Stihl"),
            (today - timedelta(25), "45.00", "Fuel", "Monthly gas"),
            (today - timedelta(10), "200.00", "Equipment", "Splitting maul + wedges"),
            (today - timedelta(5), "60.00", "Fuel", "Diesel for delivery truck"),
        ]
        for exp_date, amount, category, notes in expense_data:
            Expense.objects.get_or_create(
                date=exp_date,
                category=category,
                notes=notes,
                defaults={
                    "amount": Decimal(amount),
                    "recorded_by": travis,
                },
            )
        self.stdout.write(f"  Created {len(expense_data)} expense records")

        # Wood inventory
        inventory_data = [
            ("Oak", "4.00", "available", "", "South rack", today - timedelta(20), None, "Seasoned, ready to sell"),
            ("Oak", "2.00", "spoken_for", "Peterson family", "South rack", today - timedelta(20), None, "Pickup next week"),
            ("Walnut", "1.50", "available", "", "Drying shed", today - timedelta(10), None, "Needs 2 more weeks to season"),
            ("Mixed Hardwood", "3.00", "spoken_for", "Riverside Campground", "North pile", today - timedelta(15), None, "Campfire bundles order"),
            ("Oak", "2.00", "sold", "Johnson estate", "Delivered", today - timedelta(45), today - timedelta(30), ""),
            ("Mixed Hardwood", "1.00", "sold", "Miller farm", "Delivered", today - timedelta(50), today - timedelta(45), ""),
            ("Oak", "3.00", "available", "", "Creek lot — stacked", today - timedelta(5), None, "Fresh cut, needs splitting"),
        ]
        inv_created = 0
        for wood_type, qty, status, buyer, location, date_added, date_sold, notes in inventory_data:
            _, was_created = WoodInventory.objects.get_or_create(
                wood_type=wood_type,
                quantity=Decimal(qty),
                status=status,
                buyer=buyer,
                defaults={
                    "location": location,
                    "date_added": date_added,
                    "date_sold": date_sold,
                    "notes": notes,
                    "recorded_by": travis,
                },
            )
            if was_created:
                inv_created += 1
        self.stdout.write(f"  Created {inv_created} inventory items")

        self.stdout.write(self.style.SUCCESS("\nSeed complete!"))
