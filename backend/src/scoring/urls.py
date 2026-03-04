# src/scoring/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from src.scoring.views.ccf_upload_view import CCFUploadViewSet
from src.scoring.views.scoring_view import CarrierViewSet

router = DefaultRouter()
router.register(r"carriers", CarrierViewSet, basename="carrier")
router.register(r"uploads", CCFUploadViewSet, basename="ccf-upload")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "ccf/upload/",
        CCFUploadViewSet.as_view({"post": "upload"}),
        name="ccf-upload-direct",
    ),
]