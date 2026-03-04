from django.urls import path, include
from rest_framework.routers import DefaultRouter
from src.scoring.views.ccf_upload_view import CCFUploadViewSet

router = DefaultRouter()
router.register(r"ccf/uploads", CCFUploadViewSet, basename="ccf-upload")

# The /api/ccf/upload POST endpoint is registered as a custom action on the viewset.
# DefaultRouter generates: POST /api/ccf/uploads/upload/
# We also add a direct alias at /api/ccf/upload/ for the spec requirement.
urlpatterns = [
    path("", include(router.urls)),
    path(
        "ccf/upload/",
        CCFUploadViewSet.as_view({"post": "upload"}),
        name="ccf-upload-direct",
    ),
]
