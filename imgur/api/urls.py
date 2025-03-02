from django.urls import path

from .upload import UploadCSVView
from .status import JobStatusView

urlpatterns = [
    path("upload/", UploadCSVView.as_view(), name="upload"),
    path("status/<str:job_id>/", JobStatusView.as_view(), name="status"),
]
