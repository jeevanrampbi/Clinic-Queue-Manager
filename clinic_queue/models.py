from django.db import models
from django.utils import timezone


class ClinicSettings(models.Model):
    clinic_name = models.CharField(max_length=120, default="Neighbourhood Clinic")
    avg_consultation_minutes = models.PositiveIntegerField(default=10)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Clinic settings"

    def __str__(self):
        return self.clinic_name

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Patient(models.Model):
    STATUS_WAITING = "waiting"
    STATUS_IN_CONSULTATION = "in_consultation"
    STATUS_COMPLETED = "completed"
    STATUS_SKIPPED = "skipped"

    STATUS_CHOICES = [
        (STATUS_WAITING, "Waiting"),
        (STATUS_IN_CONSULTATION, "In consultation"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_SKIPPED, "Skipped"),
    ]

    token_number = models.PositiveIntegerField()
    name = models.CharField(max_length=120)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_WAITING
    )
    queue_date = models.DateField(default=timezone.localdate)
    created_at = models.DateTimeField(auto_now_add=True)
    called_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["token_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["token_number", "queue_date"],
                name="unique_token_per_day",
            )
        ]

    def __str__(self):
        return f"#{self.token_number} {self.name}"
