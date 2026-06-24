from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from apps.expeditions.models import Expedition, ExpeditionMember


class ExpeditionConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        if user.is_anonymous:
            await self.close(code=4001)
            return

        self.group_names = await self._expedition_groups(user)
        for group_name in self.group_names:
            await self.channel_layer.group_add(group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        for group_name in getattr(self, "group_names", []):
            await self.channel_layer.group_discard(group_name, self.channel_name)

    async def expedition_event(self, event):
        await self.send_json(event["data"])

    @database_sync_to_async
    def _expedition_groups(self, user):
        chief_ids = Expedition.objects.filter(chief=user).values_list("id", flat=True)
        member_ids = ExpeditionMember.objects.filter(user=user).values_list(
            "expedition_id",
            flat=True,
        )
        expedition_ids = set(chief_ids) | set(member_ids)
        return [f"expedition_{expedition_id}" for expedition_id in expedition_ids]
