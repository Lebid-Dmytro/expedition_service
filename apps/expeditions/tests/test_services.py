from datetime import timedelta

import pytest
from django.utils import timezone

from apps.expeditions.exceptions import ExpeditionServiceError
from apps.expeditions.models import ExpeditionStatus, MemberState
from apps.expeditions.services import (
    confirm_membership,
    create_expedition,
    finish_expedition,
    invite_member,
    mark_ready,
    start_expedition,
)
from apps.users.models import User, UserRole


@pytest.fixture
def member2(db):
    return User.objects.create_user(
        email="member2@example.com",
        password="password123",
        name="Member 2",
        role=UserRole.MEMBER,
    )


@pytest.fixture
def member3(db):
    return User.objects.create_user(
        email="member3@example.com",
        password="password123",
        name="Member 3",
        role=UserRole.MEMBER,
    )


def _confirm(expedition, user):
    membership = expedition.memberships.get(user=user)
    membership.state = MemberState.CONFIRMED
    membership.confirmed_at = timezone.now()
    membership.save(update_fields=["state", "confirmed_at"])
    return membership


def test_create_expedition(chief):
    expedition = create_expedition(
        chief,
        title="Trip",
        start_at=timezone.now() + timedelta(days=1),
        capacity=3,
    )
    assert expedition.status == ExpeditionStatus.DRAFT
    assert expedition.chief == chief


def test_invite_only_member_role(chief, expedition, member):
    chief_user = User.objects.create_user(
        email="another-chief@example.com",
        password="password123",
        name="Another chief",
        role=UserRole.CHIEF,
    )
    with pytest.raises(ExpeditionServiceError):
        invite_member(expedition, chief_user)


def test_duplicate_invite(chief, expedition, member):
    invite_member(expedition, member)
    with pytest.raises(ExpeditionServiceError):
        invite_member(expedition, member)


def test_confirm_only_invited_user(chief, expedition, member, outsider):
    invite_member(expedition, member)
    with pytest.raises(ExpeditionServiceError):
        confirm_membership(expedition, outsider)


def test_confirm_changes_state(chief, expedition, member):
    invite_member(expedition, member)
    membership = confirm_membership(expedition, member)
    assert membership.state == MemberState.CONFIRMED
    assert membership.confirmed_at is not None


def test_draft_to_ready(chief, expedition):
    mark_ready(expedition)
    expedition.refresh_from_db()
    assert expedition.status == ExpeditionStatus.READY


def test_cannot_skip_to_active(chief, expedition):
    with pytest.raises(ExpeditionServiceError):
        start_expedition(expedition)


def test_start_requires_two_confirmed(chief, expedition, member, member2):
    expedition.start_at = timezone.now() - timedelta(minutes=1)
    expedition.save(update_fields=["start_at"])

    invite_member(expedition, member)
    mark_ready(expedition)
    expedition.refresh_from_db()

    with pytest.raises(ExpeditionServiceError):
        start_expedition(expedition)


def test_start_requires_start_time(chief, expedition, member, member2):
    invite_member(expedition, member)
    invite_member(expedition, member2)
    _confirm(expedition, member)
    _confirm(expedition, member2)
    mark_ready(expedition)
    expedition.refresh_from_db()

    with pytest.raises(ExpeditionServiceError):
        start_expedition(expedition)


def test_start_fails_when_over_capacity(chief, expedition, member, member2, member3):
    expedition.capacity = 2
    expedition.start_at = timezone.now() - timedelta(minutes=1)
    expedition.save(update_fields=["capacity", "start_at"])

    invite_member(expedition, member)
    invite_member(expedition, member2)
    invite_member(expedition, member3)
    _confirm(expedition, member)
    _confirm(expedition, member2)
    _confirm(expedition, member3)
    mark_ready(expedition)
    expedition.refresh_from_db()

    with pytest.raises(ExpeditionServiceError):
        start_expedition(expedition)


def test_start_success(chief, expedition, member, member2):
    expedition.start_at = timezone.now() - timedelta(minutes=1)
    expedition.save(update_fields=["start_at"])

    invite_member(expedition, member)
    invite_member(expedition, member2)
    _confirm(expedition, member)
    _confirm(expedition, member2)
    mark_ready(expedition)
    expedition.refresh_from_db()

    start_expedition(expedition)
    expedition.refresh_from_db()
    assert expedition.status == ExpeditionStatus.ACTIVE


def test_member_cannot_be_in_two_active_expeditions(chief, expedition, member, member2):
    other = create_expedition(
        chief,
        title="Other trip",
        start_at=timezone.now() - timedelta(minutes=1),
        capacity=3,
    )
    for exp in (expedition, other):
        exp.start_at = timezone.now() - timedelta(minutes=1)
        exp.save(update_fields=["start_at"])
        invite_member(exp, member)
        invite_member(exp, member2)
        _confirm(exp, member)
        _confirm(exp, member2)
        mark_ready(exp)
        exp.refresh_from_db()

    start_expedition(expedition)

    with pytest.raises(ExpeditionServiceError):
        start_expedition(other)


def test_finished_expedition_cannot_go_ready_again(chief, expedition, member, member2):
    expedition.start_at = timezone.now() - timedelta(minutes=1)
    expedition.save(update_fields=["start_at"])
    invite_member(expedition, member)
    invite_member(expedition, member2)
    _confirm(expedition, member)
    _confirm(expedition, member2)
    mark_ready(expedition)
    expedition.refresh_from_db()
    start_expedition(expedition)
    finish_expedition(expedition)
    expedition.refresh_from_db()

    with pytest.raises(ExpeditionServiceError):
        mark_ready(expedition)
