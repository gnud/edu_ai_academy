from django.conf import settings
from django.db import models


class Classroom(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class ClassSession(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        LIVE = "live", "Live"
        ENDED = "ended", "Ended"
        CANCELED = "canceled", "Canceled"

    course = models.ForeignKey(
        "academy.Course",
        on_delete=models.CASCADE,
        related_name="sessions",
    )
    classroom = models.ForeignKey(
        "liveclasses.Classroom",
        on_delete=models.PROTECT,
        related_name="sessions",
    )

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=Status.choices)

    professor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="led_sessions",
    )

    ai_agent = models.ForeignKey(
        "academy.AIAgent",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="sessions",
    )

    video_call_provider = models.CharField(max_length=50, blank=True)
    video_call_room_id = models.CharField(max_length=255, blank=True)
    video_call_join_url = models.URLField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_sessions",
    )

    created_at = models.DateTimeField(auto_now_add=True)
