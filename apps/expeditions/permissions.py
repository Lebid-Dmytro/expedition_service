from rest_framework.permissions import BasePermission

from apps.users.models import UserRole


class IsChiefRole(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == UserRole.CHIEF


class IsExpeditionChief(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.chief_id == request.user.id


class IsExpeditionParticipant(BasePermission):
    def has_object_permission(self, request, view, obj):
        if obj.chief_id == request.user.id:
            return True
        return obj.memberships.filter(user=request.user).exists()
