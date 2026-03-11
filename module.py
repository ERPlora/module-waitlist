from django.utils.translation import gettext_lazy as _

MODULE_ID = "waitlist"
MODULE_NAME = _("Waitlist")
MODULE_ICON = "people-outline"
MODULE_VERSION = "1.0.0"
MODULE_CATEGORY = "pos"

MODULE_INDUSTRIES = ["hair_salon", "barber_shop", "restaurant", "bar"]

MENU = {
    "label": _("Waitlist"),
    "icon": "people-outline",
    "order": 47,
    "show": True,
}

NAVIGATION = [
    {"id": "queue", "label": _("Queue"), "icon": "people-outline", "view": ""},
    {"id": "display", "label": _("Display"), "icon": "tv-outline", "view": "display"},
    {"id": "settings", "label": _("Settings"), "icon": "settings-outline", "view": "settings"},
]

DEPENDENCIES = []

SETTINGS = {
    "average_service_time": 30,
    "max_queue_size": 20,
}

PERMISSIONS = [
    ("view_waitlist", _("Can view waitlist")),
    ("manage_waitlist", _("Can manage waitlist")),
    ("view_settings", _("Can view settings")),
    ("change_settings", _("Can change settings")),
]

ROLE_PERMISSIONS = {
    "admin": ["*"],
    "manager": ["view_waitlist", "manage_waitlist", "view_settings", "change_settings"],
    "employee": ["view_waitlist", "manage_waitlist"],
}
