"""URL configuration for the coffee-shop backend. Everything lives under /api/ (SDD 7.1)."""

from django.conf import settings
from django.contrib import admin
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from common.views import health

urlpatterns = [
    path("api/health/", health, name="health"),
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]

# The Django admin exists only in development (SDD 11.1).
if settings.DEBUG:
    urlpatterns.append(path("admin/", admin.site.urls))

handler404 = "common.views.json_404"
handler500 = "common.views.json_500"
