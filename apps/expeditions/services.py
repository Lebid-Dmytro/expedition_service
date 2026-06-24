from django.db import transaction
from django.utils import timezone

from apps.expeditions.events import (
    notify_expedition_status,
    notify_member_confirmed,
    notify_member_invited,
)
from apps.expeditions.exceptions import ExpeditionServiceError
from apps.expeditions.models import (
    Expedition,
    ExpeditionMember,
    ExpeditionStatus,
    MemberState,
)
from apps.users.models import UserRole

ALLOWED_TRANSITIONS = {
    ExpeditionStatus.DRAFT: {ExpeditionStatus.READY},
    ExpeditionStatus.READY: {ExpeditionStatus.ACTIVE},
    ExpeditionStatus.ACTIVE: {ExpeditionStatus.FINISHED},
}


def create_expedition(chief, **fields):
    return Expedition.objects.create(
        chief=chief,
        status=ExpeditionStatus.DRAFT,
        **fields,
    )


def update_expedition(expedition, **fields):
    if expedition.status != ExpeditionStatus.DRAFT:
        raise ExpeditionServiceError("Expedition can only be updated in draft status.")

    for name, value in fields.items():
        setattr(expedition, name, value)
    expedition.save()
    return expedition


@transaction.atomic
def invite_member(expedition, member):
    expedition = Expedition.objects.select_for_update().get(pk=expedition.pk)
    if expedition.status != ExpeditionStatus.DRAFT:
        raise ExpeditionServiceError("Members can only be invited in draft status.")

    if member.role != UserRole.MEMBER:
        raise ExpeditionServiceError("Only users with member role can be invited.")

    if ExpeditionMember.objects.filter(expedition=expedition, user=member).exists():
        raise ExpeditionServiceError("User is already invited to this expedition.")

    membership = ExpeditionMember.objects.create(expedition=expedition, user=member)
    notify_member_invited(expedition.id, member.id, membership.id)
    return membership


@transaction.atomic
def confirm_membership(expedition, user):
    expedition = Expedition.objects.select_for_update().get(pk=expedition.pk)
    if expedition.status != ExpeditionStatus.DRAFT:
        raise ExpeditionServiceError("Can only confirm while expedition is in draft.")

    try:
        membership = ExpeditionMember.objects.select_for_update().get(
            expedition=expedition,
            user=user,
        )
    except ExpeditionMember.DoesNotExist:
        raise ExpeditionServiceError("You are not invited to this expedition.") from None

    if membership.state != MemberState.INVITED:
        raise ExpeditionServiceError("Membership is not in invited state.")

    membership.state = MemberState.CONFIRMED
    membership.confirmed_at = timezone.now()
    membership.save(update_fields=["state", "confirmed_at"])

    notify_member_confirmed(expedition.id, user.id, membership.id)
    return membership


def _change_status(expedition, new_status):
    expedition = Expedition.objects.select_for_update().get(pk=expedition.pk)
    allowed = ALLOWED_TRANSITIONS.get(expedition.status, set())
    if new_status not in allowed:
        raise ExpeditionServiceError(
            f"Cannot change status from '{expedition.status}' to '{new_status}'."
        )
    return expedition


@transaction.atomic
def mark_ready(expedition):
    expedition = _change_status(expedition, ExpeditionStatus.READY)
    expedition.status = ExpeditionStatus.READY
    expedition.save(update_fields=["status", "updated_at"])
    notify_expedition_status(expedition.id, expedition.status)
    return expedition


@transaction.atomic
def start_expedition(expedition):
    expedition = _change_status(expedition, ExpeditionStatus.ACTIVE)

    if expedition.start_at > timezone.now():
        raise ExpeditionServiceError("Expedition start time has not been reached.")

    confirmed = list(
        ExpeditionMember.objects.select_for_update().filter(
            expedition=expedition,
            state=MemberState.CONFIRMED,
        )
    )
    confirmed_count = len(confirmed)

    if confirmed_count < 2:
        raise ExpeditionServiceError("At least 2 confirmed members are required.")
    if confirmed_count > expedition.capacity:
        raise ExpeditionServiceError("Confirmed members exceed expedition capacity.")

    user_ids = [membership.user_id for membership in confirmed]
    in_other_active = ExpeditionMember.objects.filter(
        user_id__in=user_ids,
        state=MemberState.CONFIRMED,
        expedition__status=ExpeditionStatus.ACTIVE,
    ).exclude(expedition=expedition).exists()
    if in_other_active:
        raise ExpeditionServiceError(
            "A confirmed member is already in another active expedition."
        )

    expedition.status = ExpeditionStatus.ACTIVE
    expedition.save(update_fields=["status", "updated_at"])
    notify_expedition_status(expedition.id, expedition.status)
    return expedition


@transaction.atomic
def finish_expedition(expedition):
    expedition = _change_status(expedition, ExpeditionStatus.FINISHED)
    expedition.status = ExpeditionStatus.FINISHED
    expedition.save(update_fields=["status", "updated_at"])
    notify_expedition_status(expedition.id, expedition.status)
    return expedition
