from django.contrib import admin
from .models import (
    Taluk,
    RailwayGate,
    GateOperator,
    TalukRequest,
    TalukChangeRequest,
    GateActivityLog,
)


@admin.register(Taluk)
class TalukAdmin(admin.ModelAdmin):
    list_display = ("name", "district", "state")


@admin.register(RailwayGate)
class RailwayGateAdmin(admin.ModelAdmin):
    list_display = ("gate_name", "taluk", "status", "is_approved", "created_by")
    list_filter = ("is_approved", "taluk", "status")
    search_fields = ("gate_name", "landmark")

    def save_model(self, request, obj, form, change):
        """
        Auto-assign gate to operator who created it
        when admin approves the gate
        """
        super().save_model(request, obj, form, change)

        if obj.is_approved and obj.created_by:
            try:
                operator_profile = GateOperator.objects.get(user=obj.created_by)
                operator_profile.assigned_gate = obj
                operator_profile.save()
            except GateOperator.DoesNotExist:
                pass


@admin.register(GateOperator)
class GateOperatorAdmin(admin.ModelAdmin):
    list_display = ("user", "current_taluk", "assigned_gate")


@admin.register(TalukRequest)
class TalukRequestAdmin(admin.ModelAdmin):
    list_display = ("requested_name", "district", "requested_by", "is_approved")

    def save_model(self, request, obj, form, change):
        """
        When admin approves taluk request,
        automatically create new Taluk in system
        """
        super().save_model(request, obj, form, change)

        if obj.is_approved:
            Taluk.objects.get_or_create(
                name=obj.requested_name,
                district=obj.district,
                state="Karnataka"
            )


@admin.register(TalukChangeRequest)
class TalukChangeRequestAdmin(admin.ModelAdmin):
    list_display = ("operator", "requested_taluk", "is_approved", "created_at")

    def save_model(self, request, obj, form, change):
        """
        When admin approves taluk change:
        - Update current taluk
        - Remove old assigned gate (governance rule)
        """
        super().save_model(request, obj, form, change)

        if obj.is_approved:
            try:
                operator_profile = GateOperator.objects.get(user=obj.operator)
                operator_profile.current_taluk = obj.requested_taluk
                operator_profile.assigned_gate = None  # VERY IMPORTANT
                operator_profile.save()
            except GateOperator.DoesNotExist:
                pass

@admin.register(GateActivityLog)
class GateActivityLogAdmin(admin.ModelAdmin):
    list_display = ("gate", "operator", "action", "timestamp")
    list_filter = ("action", "gate")
    search_fields = ("gate__gate_name", "operator__username")
    ordering = ("-timestamp",)
