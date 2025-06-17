from django.urls import path
from .views import mcp_launcher, mcp_finalize

urlpatterns = [
    path('', mcp_launcher, name='mcp_launcher'),
    path('mcp_finalize/', mcp_finalize, name='mcp_finalize'),
]