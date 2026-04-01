from django.conf import settings
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

    grouping_active = models.BooleanField(default=False)

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


class ClassroomGroup(models.Model):
    """A named group of students within a session, with its own chat thread."""
    session = models.ForeignKey(
        "liveclasses.ClassSession",
        on_delete=models.CASCADE,
        related_name="groups",
    )
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    thread = models.OneToOneField(
        "communication.Thread",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="classroom_group",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.session_id})"


class ClassroomGroupMember(models.Model):
    group = models.ForeignKey(
        ClassroomGroup,
        on_delete=models.CASCADE,
        related_name="members",
    )
    participant = models.ForeignKey(
        SessionParticipant,
        on_delete=models.CASCADE,
        related_name="group_memberships",
    )

    class Meta:
        unique_together = ("group", "participant")


class BlackboardFile(models.Model):
    """A file uploaded by the professor for display on the blackboard."""
    FILE_TYPE_CHOICES = [
        ('text',     'Plain Text'),
        ('markdown', 'Markdown'),
        ('pdf',      'PDF'),
        ('image',    'Image'),
        ('video',    'Video'),
        ('audio',    'Audio'),
    ]

    session      = models.ForeignKey(ClassSession, on_delete=models.CASCADE, related_name='blackboard_files')
    name         = models.CharField(max_length=255)
    file         = models.FileField(upload_to='blackboard/%Y/%m/')
    file_type    = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES)
    uploaded_by  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    uploaded_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.name


class BlackboardState(models.Model):
    """Per-session blackboard state — polled by all participants."""
    session        = models.OneToOneField(ClassSession, on_delete=models.CASCADE, related_name='blackboard_state')
    active_file    = models.ForeignKey(BlackboardFile, on_delete=models.SET_NULL, null=True, blank=True)
    is_fullscreen  = models.BooleanField(default=False)
    is_live        = models.BooleanField(default=False)
    scroll_y       = models.IntegerField(default=0)
    zoom           = models.IntegerField(default=100)   # percentage
    rotation       = models.IntegerField(default=0)     # 0 / 90 / 180 / 270
    media_playing  = models.BooleanField(default=False)

    def __str__(self):
        return f"BlackboardState({self.session_id})"
