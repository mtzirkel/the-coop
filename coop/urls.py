from django.urls import path

from . import views

app_name = "coop"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("hours/", views.hours_list, name="hours"),
    path("hours/log/", views.log_hours, name="log_hours"),
    path("hours/team/", views.team_hours, name="team_hours"),
    path("approvals/", views.approval_queue, name="approvals"),
    path("approvals/<uuid:entry_id>/approve/", views.approve_entry, name="approve"),
    path("approvals/<uuid:entry_id>/reject/", views.reject_entry, name="reject"),
    path("inventory/", views.inventory, name="inventory"),
    path("finances/", views.finances, name="finances"),
    path("jobs/", views.manage_jobs, name="manage_jobs"),
    path("jobs/<uuid:job_id>/toggle/", views.toggle_job, name="toggle_job"),
    path("jobs/<uuid:job_id>/delete/", views.delete_job, name="delete_job"),
]
