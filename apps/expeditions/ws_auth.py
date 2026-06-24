from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken

from apps.users.models import User


@database_sync_to_async
def _get_user(user_id):
    try:
        return User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        scope["user"] = await self._user_from_scope(scope)
        return await super().__call__(scope, receive, send)

    async def _user_from_scope(self, scope):
        token = self._token_from_query(scope.get("query_string", b"").decode())
        if not token:
            return AnonymousUser()

        try:
            access = AccessToken(token)
        except (InvalidToken, TokenError):
            return AnonymousUser()

        return await _get_user(access["user_id"])

    @staticmethod
    def _token_from_query(query_string):
        for part in query_string.split("&"):
            if part.startswith("token="):
                return part.split("=", 1)[1]
        return None
