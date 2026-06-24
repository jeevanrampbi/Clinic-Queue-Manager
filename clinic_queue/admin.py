from django.contrib import admin

from .models import ClinicSettings, Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("token_number", "name", "status", "queue_date", "created_at")
    list_filter = ("status", "queue_date")


admin.site.register(ClinicSettings)
