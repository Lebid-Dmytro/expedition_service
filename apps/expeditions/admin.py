from django.contrib import admin

from apps.expeditions.models import Expedition, ExpeditionMember


class ExpeditionMemberInline(admin.TabularInline):
    model = ExpeditionMember
    extra = 0
    readonly_fields = ("invited_at", "confirmed_at")


@admin.register(Expedition)
class ExpeditionAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "chief", "start_at", "capacity", "created_at")
    list_filter = ("status",)
    search_fields = ("title", "chief__email")
    inlines = [ExpeditionMemberInline]
