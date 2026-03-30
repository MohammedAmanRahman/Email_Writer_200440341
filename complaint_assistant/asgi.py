"""ASGI config for complaint_assistant project."""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "complaint_assistant.settings")
application = get_asgi_application()
