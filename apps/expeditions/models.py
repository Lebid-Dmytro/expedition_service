from django.conf import settings
from django.db import models


class ExpeditionStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    READY = "ready", "Ready"
    ACTIVE = "active", "Active"
    FINISHED = "finished", "Finished"


class Expedition(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    status = models.CharField(
        max_length=10,
        choices=ExpeditionStatus.choices,
        default=ExpeditionStatus.DRAFT,
    )
    start_at = models.DateTimeField()
    end_at = models.DateTimeField(null=True, blank=True)
    capacity = models.PositiveIntegerField()
    chief = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="led_expeditions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "expeditions"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(capacity__gte=1),
                name="expedition_capacity_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(end_at__isnull=True)
                | models.Q(end_at__gte=models.F("start_at")),
                name="expedition_end_at_after_start_at",
            ),
        ]

    def __str__(self):
        return self.title


class MemberState(models.TextChoices):
    INVITED = "invited", "Invited"
    CONFIRMED = "confirmed", "Confirmed"


class ExpeditionMember(models.Model):
    expedition = models.ForeignKey(
        Expedition,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="expedition_memberships",
    )
    state = models.CharField(
        max_length=10,
        choices=MemberState.choices,
        default=MemberState.INVITED,
    )
    invited_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "expedition_members"
        constraints = [
            models.UniqueConstraint(
                fields=["expedition", "user"],
                name="unique_expedition_member",
            ),
        ]

    def __str__(self):
        return f"{self.user_id} -> {self.expedition_id} ({self.state})"
