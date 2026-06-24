from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.expeditions.models import ExpeditionStatus, MemberState
from apps.users.models import UserRole


def _register(client, email, name, role):
    response = client.post(
        "/api/auth/register/",
        {"email": email, "name": name, "role": role, "password": "password123"},
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED


def _token(client, email):
    response = client.post(
        "/api/auth/token/",
        {"email": email, "password": "password123"},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    return response.data["access"]


@pytest.mark.django_db
def test_expedition_happy_path():
    client = APIClient()

    _register(client, "chief@example.com", "Chief", UserRole.CHIEF)
    _register(client, "member1@example.com", "Member 1", UserRole.MEMBER)
    _register(client, "member2@example.com", "Member 2", UserRole.MEMBER)

    chief_token = _token(client, "chief@example.com")
    member1_token = _token(client, "member1@example.com")
    member2_token = _token(client, "member2@example.com")

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {chief_token}")
    create_response = client.post(
        "/api/expeditions/",
        {
            "title": "Arctic trip",
            "start_at": (timezone.now() - timedelta(minutes=5)).isoformat(),
            "capacity": 5,
        },
        format="json",
    )
    assert create_response.status_code == status.HTTP_201_CREATED
    expedition_id = create_response.data["id"]
    assert create_response.data["status"] == ExpeditionStatus.DRAFT

    for email in ("member1@example.com", "member2@example.com"):
        invite_response = client.post(
            f"/api/expeditions/{expedition_id}/invite/",
            {"email": email},
            format="json",
        )
        assert invite_response.status_code == status.HTTP_201_CREATED

    for token in (member1_token, member2_token):
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        confirm_response = client.post(f"/api/expeditions/{expedition_id}/confirm/")
        assert confirm_response.status_code == status.HTTP_200_OK
        assert confirm_response.data["state"] == MemberState.CONFIRMED

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {chief_token}")

    ready_response = client.post(f"/api/expeditions/{expedition_id}/ready/")
    assert ready_response.status_code == status.HTTP_200_OK
    assert ready_response.data["status"] == ExpeditionStatus.READY

    start_response = client.post(f"/api/expeditions/{expedition_id}/start/")
    assert start_response.status_code == status.HTTP_200_OK
    assert start_response.data["status"] == ExpeditionStatus.ACTIVE

    finish_response = client.post(f"/api/expeditions/{expedition_id}/finish/")
    assert finish_response.status_code == status.HTTP_200_OK
    assert finish_response.data["status"] == ExpeditionStatus.FINISHED


@pytest.mark.django_db
def test_member_cannot_create_expedition():
    client = APIClient()

    _register(client, "chief2@example.com", "Chief", UserRole.CHIEF)
    _register(client, "member-only@example.com", "Member", UserRole.MEMBER)

    token = _token(client, "member-only@example.com")
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    response = client.post(
        "/api/expeditions/",
        {
            "title": "Forbidden trip",
            "start_at": timezone.now().isoformat(),
            "capacity": 3,
        },
        format="json",
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
