from django.contrib import admin

from .models import CoopMember, Expense, Income, Job, TimeEntry, WoodInventory


@admin.register(CoopMember)
class CoopMemberAdmin(admin.ModelAdmin):
    list_display = ["display_name", "username", "role", "approver", "is_active"]
    list_filter = ["role", "is_active"]
    search_fields = ["display_name", "username"]


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ["name", "rate_multiplier", "is_active"]
    list_filter = ["is_active"]


@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = ["member", "job", "date", "hours", "status", "approved_by"]
    list_filter = ["status", "job", "date"]
    search_fields = ["member__display_name", "notes"]
    date_hierarchy = "date"


@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = ["date", "amount", "source", "recorded_by"]
    date_hierarchy = "date"


@admin.register(WoodInventory)
class WoodInventoryAdmin(admin.ModelAdmin):
    list_display = ["wood_type", "quantity", "status", "buyer", "location", "date_added"]
    list_filter = ["status", "wood_type"]
    search_fields = ["wood_type", "buyer", "location"]
    date_hierarchy = "date_added"


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ["date", "amount", "category", "recorded_by"]
    date_hierarchy = "date"
