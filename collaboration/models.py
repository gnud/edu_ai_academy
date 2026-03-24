from django.conf import settings
from django.db import models


class StudentGroup(models.Model):
    class GroupType(models.TextChoices):
        PAIR = "pair", "Pair"
        TEAM = "team", "Team"

    session = models.ForeignKey(
        "liveclasses.ClassSession",
        on_delete=models.CASCADE,
        related_name="student_groups",
    )

    name = models.CharField(max_length=255)
    group_type = models.CharField(max_length=20, choices=GroupType.choices)

    assignment_mode_enabled = models.BooleanField(default=False)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
    )

    created_at = models.DateTimeField(auto_now_add=True)
