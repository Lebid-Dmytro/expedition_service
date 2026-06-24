import asyncio

import pytest
from channels.testing import WebsocketCommunicator

from apps.expeditions.events import notify_expedition_status, notify_member_invited
from config.asgi import application


@pytest.mark.asyncio
async def test_anonymous_connection_is_rejected():
    communicator = WebsocketCommunicator(application, "/ws/expeditions/")
    connected, _ = await communicator.connect()
    assert connected is False


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_participant_receives_expedition_event(chief, member, expedition, membership, access_token):
    token = access_token(member)
    communicator = WebsocketCommunicator(
        application,
        f"/ws/expeditions/?token={token}",
    )

    connected, _ = await communicator.connect()
    assert connected is True

    await asyncio.to_thread(notify_expedition_status, expedition.id, "ready")

    message = await communicator.receive_json_from()
    assert message == {
        "type": "expedition_status",
        "expedition_id": expedition.id,
        "payload": {"status": "ready"},
    }

    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_outsider_does_not_receive_event(
    chief,
    member,
    outsider,
    expedition,
    membership,
    access_token,
):
    token = access_token(outsider)
    communicator = WebsocketCommunicator(
        application,
        f"/ws/expeditions/?token={token}",
    )

    connected, _ = await communicator.connect()
    assert connected is True

    await asyncio.to_thread(
        notify_member_invited,
        expedition.id,
        member.id,
        membership.id,
    )

    assert await communicator.receive_nothing(timeout=0.2) is True
    await communicator.disconnect()
