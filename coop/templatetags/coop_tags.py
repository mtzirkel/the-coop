import json

from django import template
from django.utils.safestring import mark_safe

from coop.models import Job

register = template.Library()


@register.simple_tag
def jobs_json():
    """Output active jobs as a JSON string for Svelte components."""
    jobs = list(Job.objects.filter(is_active=True).values("id", "name"))
    # Convert UUIDs to strings for JSON serialization
    for job in jobs:
        job["id"] = str(job["id"])
    return mark_safe(json.dumps(jobs))


@register.simple_tag
def other_members_json(members):
    """Serialize a list of CoopMembers to JSON for Svelte islands."""
    data = [{"id": str(m.id), "display_name": m.display_name} for m in members]
    return mark_safe(json.dumps(data))
