import uuid
from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase, override_settings


# All tests run with dev bypass so no real auth service needed
@override_settings(NOEGOS_AUTH_DEV_BYPASS=True)
class BaseCoopTest(TestCase):
    """Base test class that sets up a dev user member."""

    def setUp(self):
        from coop.models import CoopMember

        self.member = CoopMember.objects.create(
            auth_user_id=uuid.UUID(int=1),
            username="dev",
            display_name="Dev User",
            role=CoopMember.Role.ADMIN,
        )


class ModelTests(BaseCoopTest):
    def test_create_job(self):
        from coop.models import Job

        job = Job.objects.create(name="Wood Cutting", description="Cutting wood")
        self.assertEqual(str(job), "Wood Cutting")
        self.assertTrue(job.is_active)
        self.assertEqual(job.rate_multiplier, Decimal("1.00"))

    def test_create_time_entry(self):
        from coop.models import Job, TimeEntry

        job = Job.objects.create(name="Stacking")
        entry = TimeEntry.objects.create(
            member=self.member,
            job=job,
            date=date.today(),
            hours=Decimal("3.50"),
            location="North ridge",
            notes="Stacked 2 cords",
        )
        self.assertEqual(entry.status, TimeEntry.Status.PENDING)
        self.assertIsNone(entry.approved_by)
        self.assertEqual(entry.location, "North ridge")

    def test_minor_requires_approver(self):
        from coop.models import CoopMember

        minor = CoopMember.objects.create(
            auth_user_id=uuid.uuid4(),
            username="kiddo",
            display_name="Kiddo",
            role=CoopMember.Role.MINOR,
            approver=self.member,
        )
        self.assertEqual(minor.approver, self.member)
        self.assertIn(minor, self.member.dependents.all())

    def test_income_and_expense(self):
        from coop.models import Expense, Income

        income = Income.objects.create(
            date=date.today(),
            amount=Decimal("500.00"),
            source="Johnson family",
            recorded_by=self.member,
        )
        expense = Expense.objects.create(
            date=date.today(),
            amount=Decimal("45.00"),
            category="Fuel",
            recorded_by=self.member,
        )
        self.assertEqual(str(income), f"$500.00 from Johnson family on {date.today()}")
        self.assertEqual(str(expense), f"$45.00 for Fuel on {date.today()}")

    def test_create_wood_inventory(self):
        from coop.models import WoodInventory

        item = WoodInventory.objects.create(
            wood_type="Oak",
            quantity=Decimal("4.00"),
            status=WoodInventory.Status.AVAILABLE,
            location="South rack",
            date_added=date.today(),
            recorded_by=self.member,
        )
        self.assertEqual(str(item), "4.00 cords Oak (Available)")
        self.assertEqual(item.status, "available")
        self.assertIsNone(item.date_sold)


class ViewTests(BaseCoopTest):
    def test_dashboard_loads(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "The Coop")
        self.assertContains(resp, "Dev User")

    def test_hours_list(self):
        """Test hours_list view loads."""
        resp = self.client.get("/hours/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "My Hours")

    def test_hours_htmx_partial(self):
        resp = self.client.get(
            "/hours/?period=month", HTTP_HX_REQUEST="true"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "<nav")
        self.assertContains(resp, "entries")

    def test_approval_queue(self):
        """Test approval_queue view loads."""
        resp = self.client.get("/approvals/")
        self.assertEqual(resp.status_code, 200)

    def test_finances_page_loads(self):
        resp = self.client.get("/finances/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Finances")

    def test_inventory_page_loads(self):
        """Test inventory view loads."""
        resp = self.client.get("/inventory/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Wood Inventory")

    def test_log_hours_page_loads(self):
        resp = self.client.get("/hours/log/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Log Hours")

    def test_team_hours_loads_for_admin(self):
        """Test team_hours view loads for admin."""
        resp = self.client.get("/hours/team/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Team Hours")


class PermissionTests(BaseCoopTest):
    """Test require_role decorator and role-based access."""

    def _create_member_user(self, role="member"):
        """Create a non-admin member and set the dev bypass to use their ID."""
        from coop.models import CoopMember

        member = CoopMember.objects.create(
            auth_user_id=uuid.UUID(int=99),
            username="regular",
            display_name="Regular User",
            role=role,
        )
        return member

    @override_settings(
        NOEGOS_AUTH_DEV_BYPASS=True,
        NOEGOS_AUTH_DEV_USER_ID=uuid.UUID(int=99),
        NOEGOS_AUTH_DEV_USERNAME="regular",
    )
    def test_team_hours_forbidden_for_member(self):
        """Members cannot access team hours."""
        self._create_member_user("member")
        resp = self.client.get("/hours/team/")
        self.assertEqual(resp.status_code, 403)

    @override_settings(
        NOEGOS_AUTH_DEV_BYPASS=True,
        NOEGOS_AUTH_DEV_USER_ID=uuid.UUID(int=99),
        NOEGOS_AUTH_DEV_USERNAME="regular",
    )
    def test_team_hours_forbidden_for_minor(self):
        """Minors cannot access team hours."""
        self._create_member_user("minor")
        resp = self.client.get("/hours/team/")
        self.assertEqual(resp.status_code, 403)

    @override_settings(
        NOEGOS_AUTH_DEV_BYPASS=True,
        NOEGOS_AUTH_DEV_USER_ID=uuid.UUID(int=99),
        NOEGOS_AUTH_DEV_USERNAME="regular",
    )
    def test_finances_forbidden_for_minor(self):
        """Minors cannot access finances."""
        self._create_member_user("minor")
        resp = self.client.get("/finances/")
        self.assertEqual(resp.status_code, 403)

    @override_settings(
        NOEGOS_AUTH_DEV_BYPASS=True,
        NOEGOS_AUTH_DEV_USER_ID=uuid.UUID(int=99),
        NOEGOS_AUTH_DEV_USERNAME="regular",
    )
    def test_finances_forbidden_for_member(self):
        """Members cannot access finances — admin only."""
        self._create_member_user("member")
        resp = self.client.get("/finances/")
        self.assertEqual(resp.status_code, 403)

    @override_settings(
        NOEGOS_AUTH_DEV_BYPASS=True,
        NOEGOS_AUTH_DEV_USER_ID=uuid.UUID(int=99),
        NOEGOS_AUTH_DEV_USERNAME="regular",
    )
    def test_inventory_allowed_for_member(self):
        """Members can access inventory."""
        self._create_member_user("member")
        resp = self.client.get("/inventory/")
        self.assertEqual(resp.status_code, 200)

    @override_settings(
        NOEGOS_AUTH_DEV_BYPASS=True,
        NOEGOS_AUTH_DEV_USER_ID=uuid.UUID(int=99),
        NOEGOS_AUTH_DEV_USERNAME="regular",
    )
    def test_inventory_allowed_for_minor(self):
        """Minors can access inventory."""
        self._create_member_user("minor")
        resp = self.client.get("/inventory/")
        self.assertEqual(resp.status_code, 200)

    def test_admin_sees_all_pending_approvals(self):
        """Admin approval_queue shows all pending, not just their dependents."""
        from coop.models import CoopMember, Job, TimeEntry

        other_adult = CoopMember.objects.create(
            auth_user_id=uuid.uuid4(),
            username="other_adult",
            display_name="Other Adult",
        )
        other_kid = CoopMember.objects.create(
            auth_user_id=uuid.uuid4(),
            username="other_kid",
            display_name="Other Kid",
            role=CoopMember.Role.MINOR,
            approver=other_adult,
        )
        job = Job.objects.create(name="Stacking")
        TimeEntry.objects.create(
            member=other_kid,
            job=job,
            date=date.today(),
            hours=Decimal("2.00"),
            status=TimeEntry.Status.PENDING,
        )
        resp = self.client.get("/approvals/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Other Kid")

    def test_admin_can_approve_any_entry(self):
        """Admin can approve entries from any member's dependent."""
        from coop.models import CoopMember, Job, TimeEntry

        other_adult = CoopMember.objects.create(
            auth_user_id=uuid.uuid4(),
            username="neighbor2",
            display_name="Neighbor",
        )
        other_kid = CoopMember.objects.create(
            auth_user_id=uuid.uuid4(),
            username="neighbor_kid2",
            display_name="Neighbor Kid",
            role=CoopMember.Role.MINOR,
            approver=other_adult,
        )
        job = Job.objects.create(name="Cutting")
        entry = TimeEntry.objects.create(
            member=other_kid,
            job=job,
            date=date.today(),
            hours=Decimal("1.50"),
            status=TimeEntry.Status.PENDING,
        )
        resp = self.client.post(f"/approvals/{entry.id}/approve/")
        self.assertEqual(resp.status_code, 200)
        entry.refresh_from_db()
        self.assertEqual(entry.status, "approved")


class ApprovalFlowTests(BaseCoopTest):
    def setUp(self):
        super().setUp()
        from coop.models import CoopMember, Job, TimeEntry

        self.job = Job.objects.create(name="Hauling")
        self.minor = CoopMember.objects.create(
            auth_user_id=uuid.uuid4(),
            username="junior",
            display_name="Junior",
            role=CoopMember.Role.MINOR,
            approver=self.member,
        )
        self.entry = TimeEntry.objects.create(
            member=self.minor,
            job=self.job,
            date=date.today(),
            hours=Decimal("2.00"),
            status=TimeEntry.Status.PENDING,
        )

    def test_approve_entry(self):
        resp = self.client.post(f"/approvals/{self.entry.id}/approve/")
        self.assertEqual(resp.status_code, 200)
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.status, "approved")
        self.assertEqual(self.entry.approved_by, self.member)
        self.assertIsNotNone(self.entry.approved_at)

    def test_reject_entry(self):
        resp = self.client.post(f"/approvals/{self.entry.id}/reject/")
        self.assertEqual(resp.status_code, 200)
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.status, "rejected")

    def test_cannot_approve_others_dependents(self):
        """Non-admin member cannot approve another member's dependents."""
        from coop.models import CoopMember, TimeEntry

        # Change dev user to regular member for this test
        self.member.role = CoopMember.Role.MEMBER
        self.member.save()

        other_adult = CoopMember.objects.create(
            auth_user_id=uuid.uuid4(),
            username="neighbor",
            display_name="Neighbor",
        )
        other_kid = CoopMember.objects.create(
            auth_user_id=uuid.uuid4(),
            username="neighbor_kid",
            display_name="Neighbor Kid",
            role=CoopMember.Role.MINOR,
            approver=other_adult,
        )
        entry = TimeEntry.objects.create(
            member=other_kid,
            job=self.job,
            date=date.today(),
            hours=Decimal("1.00"),
            status=TimeEntry.Status.PENDING,
        )
        resp = self.client.post(f"/approvals/{entry.id}/approve/")
        self.assertEqual(resp.status_code, 404)


class APITests(BaseCoopTest):
    def test_health_endpoint(self):
        resp = self.client.get("/api/health/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"status": "ok"})

    def test_list_jobs(self):
        from coop.models import Job

        Job.objects.create(name="Cutting")
        Job.objects.create(name="Stacking")
        resp = self.client.get("/api/jobs/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 2)

    def test_create_time_entry_via_api(self):
        # The API accepts time_start/time_end and calculates hours automatically.
        # Admins and members are auto-approved; minors go to pending.
        from coop.models import Job

        job = Job.objects.create(name="Cutting")
        resp = self.client.post(
            "/api/hours/",
            data={
                "job_id": str(job.id),
                "date": str(date.today()),
                "time_start": "08:00",
                "time_end": "11:30",
                "location": "Creek lot",
                "notes": "Cut 1 cord of oak",
            },
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        # Admin member is auto-approved
        self.assertEqual(data["status"], "approved")
        self.assertEqual(data["location"], "Creek lot")
        # 08:00-11:30 = 3.5 hours, auto-calculated from start/end times
        self.assertEqual(Decimal(data["hours"]), Decimal("3.5"))

    def test_finance_summary(self):
        from coop.models import Expense, Income

        Income.objects.create(
            date=date.today(),
            amount=Decimal("1000.00"),
            source="Wood sale",
            recorded_by=self.member,
        )
        Expense.objects.create(
            date=date.today(),
            amount=Decimal("150.00"),
            category="Chainsaw fuel",
            recorded_by=self.member,
        )
        resp = self.client.get("/api/finances/summary/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(Decimal(data["total_income"]), Decimal("1000.00"))
        self.assertEqual(Decimal(data["total_expenses"]), Decimal("150.00"))
        self.assertEqual(Decimal(data["net_profit"]), Decimal("850.00"))

    def test_list_time_entries(self):
        from coop.models import Job, TimeEntry

        job = Job.objects.create(name="Cutting")
        TimeEntry.objects.create(
            member=self.member,
            job=job,
            date=date.today(),
            hours=Decimal("4.00"),
            status=TimeEntry.Status.APPROVED,
        )
        resp = self.client.get("/api/hours/?period=week")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(Decimal(data[0]["hours"]), Decimal("4.00"))

    def test_create_income(self):
        resp = self.client.post(
            "/api/income/",
            data={
                "date": str(date.today()),
                "amount": "500.00",
                "source": "Johnson family",
                "notes": "2 cords of oak",
            },
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        from coop.models import Income

        self.assertEqual(Income.objects.count(), 1)
        self.assertEqual(Income.objects.first().source, "Johnson family")

    def test_create_expense(self):
        resp = self.client.post(
            "/api/expenses/",
            data={
                "date": str(date.today()),
                "amount": "45.00",
                "category": "Chainsaw fuel",
            },
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        from coop.models import Expense

        self.assertEqual(Expense.objects.count(), 1)
        self.assertEqual(Expense.objects.first().category, "Chainsaw fuel")

    def test_member_splits(self):
        from coop.models import CoopMember, Expense, Income, Job, TimeEntry

        job = Job.objects.create(name="Cutting")
        neighbor = CoopMember.objects.create(
            auth_user_id=uuid.uuid4(),
            username="neighbor",
            display_name="Neighbor",
        )
        for hours, member in [(6, self.member), (4, neighbor)]:
            TimeEntry.objects.create(
                member=member,
                job=job,
                date=date.today(),
                hours=Decimal(str(hours)),
                status=TimeEntry.Status.APPROVED,
            )
        Income.objects.create(
            date=date.today(),
            amount=Decimal("1000.00"),
            source="Sale",
            recorded_by=self.member,
        )

        resp = self.client.get("/api/finances/splits/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 2)
        dev_split = next(s for s in data if s["name"] == "Dev User")
        self.assertAlmostEqual(dev_split["percentage"], 60.0)
        self.assertAlmostEqual(Decimal(dev_split["cut"]), Decimal("600.00"))


class AuthMiddlewareTests(TestCase):
    """Test auth behavior WITHOUT dev bypass."""

    @override_settings(NOEGOS_AUTH_DEV_BYPASS=False)
    def test_unauthenticated_redirects_to_login(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("login", resp.url)
        self.assertIn("return_to", resp.url)

    @override_settings(NOEGOS_AUTH_DEV_BYPASS=False)
    def test_public_paths_skip_auth(self):
        resp = self.client.get("/api/health/")
        self.assertEqual(resp.status_code, 200)

    @override_settings(NOEGOS_AUTH_DEV_BYPASS=True)
    def test_dev_bypass_sets_auth_user(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
