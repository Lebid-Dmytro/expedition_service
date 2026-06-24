from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


EVENT_MEMBER_INVITED = "member_invited"
EVENT_MEMBER_CONFIRMED = "member_confirmed"
EVENT_EXPEDITION_STATUS = "expedition_status"


def _group_name(expedition_id):
    return f"expedition_{expedition_id}"


def _send(expedition_id, event_type, payload):
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    async_to_sync(channel_layer.group_send)(
        _group_name(expedition_id),
        {
            "type": "expedition.event",
            "data": {
                "type": event_type,
                "expedition_id": expedition_id,
                "payload": payload,
            },
        },
    )


def notify_member_invited(expedition_id, user_id, membership_id):
    _send(
        expedition_id,
        EVENT_MEMBER_INVITED,
        {"user_id": user_id, "membership_id": membership_id},
    )


def notify_member_confirmed(expedition_id, user_id, membership_id):
    _send(
        expedition_id,
        EVENT_MEMBER_CONFIRMED,
        {"user_id": user_id, "membership_id": membership_id},
    )


def notify_expedition_status(expedition_id, status):
    _send(
        expedition_id,
        EVENT_EXPEDITION_STATUS,
        {"status": status},
    )
