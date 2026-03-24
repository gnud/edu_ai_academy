from django.conf import settings
from django.db import models


class CoursePolicy(models.Model):
    name = models.CharField(max_length=255, unique=True)

    ai_external_processing_allowed = models.BooleanField(default=True)
    client_side_ai_only = models.BooleanField(default=False)
    strict_privacy_mode = models.BooleanField(default=False)

    # Recording
    course_recording = models.BooleanField(default=False)
    course_recording_stream = models.BooleanField(default=False)
    course_recording_chat_history = models.BooleanField(default=False)
    course_recording_chat_group_history = models.BooleanField(default=False)

    # Chat permissions
    course_chat_students_allowed = models.BooleanField(default=True)
    course_chat_students_with_ai_allowed = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)
    is_system_default = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Course(models.Model):
    class AudienceType(models.TextChoices):
        ADULTS_ONLY = "adults_only", "Adults only"
        CHILDREN_ONLY = "children_only", "Children only"
        MIXED = "mixed", "Mixed"

    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)

    description = models.TextField(blank=True)
    short_description = models.CharField(max_length=500, blank=True)

    audience_type = models.CharField(
        max_length=20,
        choices=AudienceType.choices,
        default=AudienceType.MIXED,
    )

    policy = models.ForeignKey(
        "academy.CoursePolicy",
        on_delete=models.PROTECT,
        related_name="courses",
    )

    max_students = models.PositiveIntegerField(null=True, blank=True)
    enrollment_open = models.BooleanField(default=True)

    is_active = models.BooleanField(default=True)
    is_published = models.BooleanField(default=False)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_courses",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class CourseMembership(models.Model):
    class Role(models.TextChoices):
        PROFESSOR = "professor", "Professor"
        AI_PROFESSOR = "ai_professor", "AI Professor"
        STUDENT = "student", "Student"
        MODERATOR = "moderator", "Moderator"
        DEMONSTRATOR = "demonstrator", "Demonstrator"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INVITED = "invited", "Invited"
        SUSPENDED = "suspended", "Suspended"
        REMOVED = "removed", "Removed"

    course = models.ForeignKey(
        "academy.Course",
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="course_memberships",
    )

    role = models.CharField(max_length=32, choices=Role.choices)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.ACTIVE)

    can_manage_content = models.BooleanField(default=False)
    can_manage_enrollment = models.BooleanField(default=False)
    can_reply_inbox = models.BooleanField(default=False)
    can_moderate_comments = models.BooleanField(default=False)
    can_grade = models.BooleanField(default=False)
    can_manage_course_settings = models.BooleanField(default=False)

    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("course", "user", "role")


class AIAgent(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)

    description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    can_lead_sessions = models.BooleanField(default=True)
    can_answer_students = models.BooleanField(default=True)
    can_grade = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
