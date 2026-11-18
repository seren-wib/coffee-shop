"""Clients that carry a real access token from the login API (STP 3)."""

from rest_framework.test import APIClient


def auth_client(user, password="pass1234"):
    client = APIClient()
    res = client.post(
        "/api/auth/token/", {"email": user.email, "password": password}, format="json"
    )
    assert res.status_code == 200, res.content
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.json()['access']}")
    return client
