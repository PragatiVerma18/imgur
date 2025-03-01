from django.urls import path
from .views import UploadCSV
from .views import JobStatus

urlpatterns = [
    path("upload/", UploadCSV.as_view(), name="upload"),
    path("status/<str:job_id>/", JobStatus.as_view(), name="status"),
]
