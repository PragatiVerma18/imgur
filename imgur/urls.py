from django.contrib import admin
from django.urls import path, include

from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from imgur.api import urls as api_urls

schema_view = get_schema_view(
    openapi.Info(
        title="Image Processing API",
        default_version="v1",
        description="A Celery-powered image processing service that compresses images, uploads them to Cloudinary, and triggers a webhook upon job completion.",
        contact=openapi.Contact(email="itispragativerma@gmail.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path(
        "swagger<format>/", schema_view.without_ui(cache_timeout=0), name="schema-json"
    ),
    path(
        "swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path("", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
    path("admin/", admin.site.urls),
    path("api/", include(api_urls)),
]
