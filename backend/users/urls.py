from django.urls import path

from users import views

urlpatterns = [
    path("auth/register/", views.RegisterView.as_view(), name="register"),
    path("auth/token/", views.LoginView.as_view(), name="token"),
    path("auth/token/refresh/", views.RefreshView.as_view(), name="token_refresh"),
    path("me/", views.MeView.as_view(), name="me"),
    path("me/password/", views.PasswordChangeView.as_view(), name="me_password"),
]
