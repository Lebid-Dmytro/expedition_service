from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.expeditions.models import Expedition, ExpeditionMember

User = get_user_model()


class ExpeditionMemberSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_name = serializers.CharField(source="user.name", read_only=True)

    class Meta:
        model = ExpeditionMember
        fields = (
            "id",
            "user_id",
            "user_email",
            "user_name",
            "state",
            "invited_at",
            "confirmed_at",
        )


class ExpeditionSerializer(serializers.ModelSerializer):
    chief_email = serializers.EmailField(source="chief.email", read_only=True)
    members = ExpeditionMemberSerializer(source="memberships", many=True, read_only=True)

    class Meta:
        model = Expedition
        fields = (
            "id",
            "title",
            "description",
            "status",
            "start_at",
            "end_at",
            "capacity",
            "chief_id",
            "chief_email",
            "members",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "status",
            "chief_id",
            "chief_email",
            "members",
            "created_at",
            "updated_at",
        )


class ExpeditionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expedition
        fields = ("title", "description", "start_at", "end_at", "capacity")


class InviteMemberSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            self.user = User.objects.get(email=value)
        except User.DoesNotExist as exc:
            raise serializers.ValidationError("User not found.") from exc
        return value
