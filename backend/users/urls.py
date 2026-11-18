from django.urls import path

from users import views

urlpatterns = [
    path("auth/register/", views.RegisterView.as_view(), name="register"),
    path("auth/token/", views.LoginView.as_view(), name="token"),
    path("auth/token/refresh/", views.RefreshView.as_view(), name="token_refresh"),
    path("me/", views.MeView.as_view(), name="me"),
    path("me/password/", views.PasswordChangeView.as_view(), name="me_password"),
    path("me/addresses/", views.AddressListView.as_view(), name="addresses"),
    path(
        "me/addresses/<int:pk>/",
        views.AddressDetailView.as_view(),
        name="address_detail",
    ),
    path(
        "me/addresses/<int:pk>/default/",
        views.AddressDefaultView.as_view(),
        name="address_default",
    ),
]
