from django.db import models
from django.conf import settings


class SessionAssignment(models.Model):
    session = models.ForeignKey(
        "liveclasses.ClassSession",
        on_delete=models.CASCADE,
        related_name="assignments",
    )

    student_group = models.ForeignKey(
        "collaboration.StudentGroup",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )

    title = models.CharField(max_length=255)
    instructions = models.TextField(blank=True)

    due_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
    )

    created_at = models.DateTimeField(auto_now_add=True)


class AssignmentSubmission(models.Model):
    class SubmissionType(models.TextChoices):
        FILE = "file", "File"
        LINK = "link", "Link"
        TEXT = "text", "Text"

    assignment = models.ForeignKey(
        "submissions.SessionAssignment",
        on_delete=models.CASCADE,
        related_name="submissions",
    )

    student_group = models.ForeignKey(
        "collaboration.StudentGroup",
        on_delete=models.CASCADE,
    )

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
    )

    submission_type = models.CharField(max_length=20, choices=SubmissionType.choices)

    text_content = models.TextField(blank=True)
    external_url = models.URLField(blank=True)
    file = models.FileField(upload_to="submissions/", null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
