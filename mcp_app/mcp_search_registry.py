from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.psm.models import Project
# from tickets.models import Ticket

SEARCHABLE_MODELS = {
    "projects": {
        "model": Project,
        "fields": ["title", "code", "description"],
        "get_url": lambda obj: obj.get_absolute_url() if hasattr(obj, "get_absolute_url") else "#",
        "display": lambda obj: obj.title,
    },
    # "tickets": {
    #     "model": Ticket,
    #     "fields": ["title", "summary"],
    #     "get_url": lambda obj: reverse("tickets:ticket-detail", args=[obj.pk]),
    #     "display": lambda obj: f"{obj.title}",
    # },
    "users": {
        "model": get_user_model(),
        "fields": ["username", "first_name", "last_name", "email"],
        "get_url": lambda obj: reverse("user:profile", args=[obj.pk]),
        "display": lambda obj: f"{obj.get_full_name()} ({obj.username})",
    },
}