from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import api_views

router = DefaultRouter()
router.register(r"complaints", api_views.ComplaintViewSet, basename="complaint")
router.register(r"categories", api_views.CategoryViewSet, basename="category")

urlpatterns = [
    path("dashboard/", api_views.dashboard_stats, name="api-dashboard-stats"),
    path("", include(router.urls)),
]
