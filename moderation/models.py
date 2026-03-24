from django.db import models
from django.conf import settings


class Report(models.Model):
    class ReportType(models.TextChoices):
        COURSE = "course", "Course"
        USER = "user", "User"
        MESSAGE = "message", "Message"
        SESSION = "session", "Session"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_REVIEW = "in_review", "In Review"
        RESOLVED = "resolved", "Resolved"
        REJECTED = "rejected", "Rejected"

    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reports_submitted",
    )

    report_type = models.CharField(max_length=20, choices=ReportType.choices)
    target_id = models.PositiveBigIntegerField()

    reason = models.TextField()

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)

    assigned_admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="assigned_reports",
    )

    created_at = models.DateTimeField(auto_now_add=True)
