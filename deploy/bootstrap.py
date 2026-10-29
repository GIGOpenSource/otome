"""Create the first super admin when the database has no staff account yet."""
import os
import sys

sys.path.insert(0, "/app")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "uivsbe_backend.settings.pro")

import django

django.setup()

from models.models import User  # noqa: E402

username = os.environ.get("OTOME_ADMIN_USER", "admin")
password = os.environ.get("OTOME_ADMIN_PASSWORD", "change-me")
email = os.environ.get("OTOME_ADMIN_EMAIL", "admin@example.com")

if User.objects.filter(role__in=("operator", "admin", "super_admin")).exists():
    print("staff account already exists")
else:
    User.objects.create(
        username=username,
        email=email,
        password=password,
        role="super_admin",
        status=1,
    )
    print(f"created super admin {username}")
