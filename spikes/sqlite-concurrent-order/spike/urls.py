from django.urls import path

from shop import views

urlpatterns = [
    path("api/orders/", views.orders),
    path("health/", views.health),
]
