from django.db.models import Q
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.expeditions.exceptions import ExpeditionServiceError
from apps.expeditions.models import Expedition
from apps.expeditions.permissions import (
    IsChiefRole,
    IsExpeditionChief,
    IsExpeditionParticipant,
)
from apps.expeditions.serializers import (
    ExpeditionMemberSerializer,
    ExpeditionSerializer,
    ExpeditionWriteSerializer,
    InviteMemberSerializer,
)
from apps.expeditions.services import (
    confirm_membership,
    create_expedition,
    finish_expedition,
    invite_member,
    mark_ready,
    start_expedition,
    update_expedition,
)


class ExpeditionViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return (
            Expedition.objects.filter(Q(chief=user) | Q(memberships__user=user))
            .distinct()
            .prefetch_related("memberships__user", "chief")
        )

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return ExpeditionWriteSerializer
        return ExpeditionSerializer

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), IsChiefRole()]
        if self.action in ("update", "partial_update", "ready", "start", "finish", "invite"):
            return [IsAuthenticated(), IsExpeditionChief()]
        if self.action in ("retrieve", "confirm"):
            return [IsAuthenticated(), IsExpeditionParticipant()]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            expedition = create_expedition(
                chief=request.user,
                **serializer.validated_data,
            )
        except ExpeditionServiceError as exc:
            raise ValidationError(str(exc)) from exc
        return Response(
            ExpeditionSerializer(expedition).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        expedition = self.get_object()
        serializer = self.get_serializer(expedition, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        try:
            update_expedition(expedition, **serializer.validated_data)
        except ExpeditionServiceError as exc:
            raise ValidationError(str(exc)) from exc
        return Response(ExpeditionSerializer(expedition).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    @extend_schema(request=None, responses=ExpeditionSerializer)
    @action(detail=True, methods=["post"])
    def ready(self, request, pk=None):
        expedition = self.get_object()
        try:
            mark_ready(expedition)
        except ExpeditionServiceError as exc:
            raise ValidationError(str(exc)) from exc
        expedition.refresh_from_db()
        return Response(ExpeditionSerializer(expedition).data)

    @extend_schema(request=None, responses=ExpeditionSerializer)
    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        expedition = self.get_object()
        try:
            start_expedition(expedition)
        except ExpeditionServiceError as exc:
            raise ValidationError(str(exc)) from exc
        expedition.refresh_from_db()
        return Response(ExpeditionSerializer(expedition).data)

    @extend_schema(request=None, responses=ExpeditionSerializer)
    @action(detail=True, methods=["post"])
    def finish(self, request, pk=None):
        expedition = self.get_object()
        try:
            finish_expedition(expedition)
        except ExpeditionServiceError as exc:
            raise ValidationError(str(exc)) from exc
        expedition.refresh_from_db()
        return Response(ExpeditionSerializer(expedition).data)

    @extend_schema(request=InviteMemberSerializer, responses=ExpeditionMemberSerializer)
    @action(detail=True, methods=["post"])
    def invite(self, request, pk=None):
        expedition = self.get_object()
        serializer = InviteMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            membership = invite_member(expedition, serializer.user)
        except ExpeditionServiceError as exc:
            raise ValidationError(str(exc)) from exc
        return Response(
            ExpeditionMemberSerializer(membership).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(request=None, responses=ExpeditionMemberSerializer)
    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        expedition = self.get_object()
        try:
            membership = confirm_membership(expedition, request.user)
        except ExpeditionServiceError as exc:
            raise ValidationError(str(exc)) from exc
        return Response(ExpeditionMemberSerializer(membership).data)
