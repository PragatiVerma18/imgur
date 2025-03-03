from django.urls import path

from .upload import UploadCSVView
from .status import JobStatusView
from .output_csv import OutputCSVView

urlpatterns = [
    path("upload/", UploadCSVView.as_view(), name="upload"),
    path("status/<str:job_id>/", JobStatusView.as_view(), name="status"),
    path("output/<uuid:job_id>/", OutputCSVView.as_view(), name="output_csv"),
]
