from django.db import models

from apps.core import enums as core_enums


class Classroom(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class ClassSession(models.Model):
    semester = models.ForeignKey(
        "academy.Semester",
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
    status = models.CharField(
        max_length=20,
        choices=core_enums.ClassSessionStatus.choices,
        default=core_enums.ClassSessionStatus.SCHEDULED
    )

    professor = models.ForeignKey(
        "auth.User",
        on_delete=models.PROTECT,
        related_name="led_sessions",
        null=True,
        blank=True,
    )
    ai_professor_membership = models.ForeignKey(
        "academy.CourseMembership",
        on_delete=models.PROTECT,
        related_name="ai_led_sessions",
        null=True,
        blank=True,
    )

    created_by = models.ForeignKey(
        "auth.User",
        on_delete=models.PROTECT,
        related_name="created_sessions",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class SessionParticipant(models.Model):
    session = models.ForeignKey(
        "liveclasses.ClassSession",
        on_delete=models.CASCADE,
        related_name="participants",
    )
    user = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="session_participations",
        null=True,
        blank=True,
    )
    ai_agent = models.ForeignKey(
        "academy.AIAgent",
        on_delete=models.CASCADE,
        related_name="session_participations",
        null=True,
        blank=True,
    )

    role = models.CharField(max_length=32, choices=core_enums.Role.choices)
    attendance_status = models.CharField(
        max_length=20,
        choices=core_enums.AttendanceStatus.choices,
        default=core_enums.AttendanceStatus.INVITED,
    )

    joined_at = models.DateTimeField(null=True, blank=True)
    left_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                        models.Q(user__isnull=False, ai_agent__isnull=True) |
                        models.Q(user__isnull=True, ai_agent__isnull=False)
                ),
                name="session_participant_user_xor_ai_agent",
            )
        ]
