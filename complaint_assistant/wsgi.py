"""WSGI config for complaint_assistant project."""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "complaint_assistant.settings")
application = get_wsgi_application()
