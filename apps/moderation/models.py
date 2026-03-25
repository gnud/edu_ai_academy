from django.db import models

from apps.core import enums as core_enums

class CourseThread(models.Model):
    course = models.ForeignKey(
        "academy.Course",
        on_delete=models.CASCADE,
        related_name="threads",
    )
    subject = models.CharField(max_length=255)
    thread_type = models.CharField(max_length=20, choices=core_enums.ThreadType.choices)
    created_by = models.ForeignKey(
        "auth.User",
        on_delete=models.PROTECT,
        related_name="created_course_threads",
    )
    is_closed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class CourseMessage(models.Model):
    thread = models.ForeignKey(
        CourseThread,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    author = models.ForeignKey(
        "auth.User",
        on_delete=models.PROTECT,
        related_name="course_messages",
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class Report(models.Model):
    reported_by = models.ForeignKey(
        "auth.User",
        on_delete=models.PROTECT,
        related_name="submitted_reports",
    )

    report_type = models.CharField(max_length=20, choices=core_enums.ReportType.choices)
    target_id = models.PositiveBigIntegerField()
    reason = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=core_enums.ReportStatus.choices,
        default=core_enums.ReportStatus.OPEN
    )

    assigned_admin = models.ForeignKey(
        "auth.User",
        on_delete=models.PROTECT,
        related_name="assigned_reports",
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
