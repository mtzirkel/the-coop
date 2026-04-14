from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from django.views.static import serve

from coop.api.endpoints import api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
    path("manifest.json", serve, {"document_root": "static", "path": "manifest.json"}),
    path("sw.js", serve, {"document_root": "static", "path": "sw.js"}),
    path("", include("coop.urls")),
]
