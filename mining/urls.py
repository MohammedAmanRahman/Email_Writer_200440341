from django.urls import path

from . import views

app_name = "mining"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("api/data/", views.dashboard_api, name="dashboard_api"),
    path("associations/", views.association_rules, name="associations"),
    path("clusters/", views.cluster_view, name="clusters"),
]
