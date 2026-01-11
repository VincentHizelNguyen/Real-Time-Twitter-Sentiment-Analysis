from django.urls import path
from . import views

urlpatterns = [
    path("", views.index),
    path("api/overview/", views.api_overview),
    path("api/series/", views.api_series),
    path("api/latest/", views.api_latest),
]
