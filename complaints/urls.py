from django.urls import path

from . import views

app_name = "complaints"

urlpatterns = [
    path("", views.submit_complaint, name="submit"),
    path("<int:pk>/", views.complaint_detail, name="detail"),
    path("history/", views.complaint_history, name="history"),
    path("<int:pk>/letter/", views.generate_letter, name="generate_letter"),
    path("<int:pk>/delete/", views.delete_complaint, name="delete"),
    path("data/", views.data_collected, name="data_collected"),
    path("train/", views.train_letters, name="train_letters"),
    path("train/<int:pk>/delete/", views.delete_example, name="delete_example"),
    path("<int:pk>/similar/", views.similar_style, name="similar_style"),
    path("api/search-companies/", views.search_companies, name="search_companies"),
]
