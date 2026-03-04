from django.urls import include, path

from src.scoring.views.scoring_view import HealthCheckView

urlpatterns = [
    path("api/health/", HealthCheckView.as_view(), name="health-check"),
    path("api/", include("src.scoring.urls")),
]
