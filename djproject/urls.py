# project urls.py
from django.views.generic import TemplateView
from django.contrib import admin
from django.urls import path, include
from oauth2_provider import urls as oauth2_urls

urlpatterns = [
    path("", TemplateView.as_view(template_name="home.html"), name="home"),
    path("admin/", admin.site.urls),
    path("o/", include(oauth2_urls)),
    path("mcp-demo/", include("mcp_app.urls")),  
]