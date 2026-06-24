from datetime import timedelta

import pytest
from django.utils import timezone


@pytest.fixture(autouse=True)
def inmemory_channel_layer(settings):
    settings.CHANNEL_LAYERS = {
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
    }


@pytest.fixture
def chief(db):
    from apps.users.models import User, UserRole

    return User.objects.create_user(
        email="chief@example.com",
        password="password123",
        name="Chief",
        role=UserRole.CHIEF,
    )


@pytest.fixture
def member(db):
    from apps.users.models import User, UserRole

    return User.objects.create_user(
        email="member@example.com",
        password="password123",
        name="Member",
        role=UserRole.MEMBER,
    )


@pytest.fixture
def outsider(db):
    from apps.users.models import User, UserRole

    return User.objects.create_user(
        email="outsider@example.com",
        password="password123",
        name="Outsider",
        role=UserRole.MEMBER,
    )


@pytest.fixture
def expedition(chief):
    from apps.expeditions.models import Expedition, ExpeditionStatus

    return Expedition.objects.create(
        title="Arctic trip",
        status=ExpeditionStatus.DRAFT,
        start_at=timezone.now() + timedelta(days=1),
        capacity=5,
        chief=chief,
    )


@pytest.fixture
def membership(expedition, member):
    from apps.expeditions.models import ExpeditionMember, MemberState

    return ExpeditionMember.objects.create(
        expedition=expedition,
        user=member,
        state=MemberState.INVITED,
    )


@pytest.fixture
def access_token():
    from rest_framework_simplejwt.tokens import AccessToken

    def _for_user(user):
        return str(AccessToken.for_user(user))

    return _for_user
