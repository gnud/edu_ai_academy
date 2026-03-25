from django.db import models
from django.core.exceptions import ValidationError

from apps.core import enums as core_enums


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


class Course(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    short_description = models.CharField(max_length=500, blank=True)

    is_active = models.BooleanField(default=True)
    is_published = models.BooleanField(default=False)

    max_students = models.PositiveIntegerField(null=True, blank=True)
    enrollment_open = models.BooleanField(default=True)

    audience_type = models.CharField(
        max_length=20,
        choices=core_enums.AudienceType.choices,
        default=core_enums.AudienceType.MIXED,
    )

    created_by = models.ForeignKey(
        "auth.User",
        on_delete=models.PROTECT,
        related_name="created_courses",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class CoursePolicy(models.Model):
    course = models.OneToOneField(
        "academy.Course",
        on_delete=models.CASCADE,
        related_name="policy",
    )

    name = models.CharField(max_length=255, unique=True)

    ai_external_processing_allowed = models.BooleanField(default=True)
    client_side_ai_only = models.BooleanField(default=False)
    strict_privacy_mode = models.BooleanField(default=False)

    course_recording = models.BooleanField(default=False)
    course_recording_stream = models.BooleanField(default=False)
    course_recording_chat_history = models.BooleanField(default=False)
    course_recording_chat_group_history = models.BooleanField(default=False)

    course_chat_students_allowed = models.BooleanField(default=True)
    course_chat_students_with_ai_allowed = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)
    is_system_default = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if not self.course_recording:
            if self.course_recording_stream:
                raise ValidationError(
                    {
                        "course_recording_stream":
                            "Stream recording cannot be enabled when course_recording is disabled."
                    }
                )
            if self.course_recording_chat_history:
                raise ValidationError(
                    {"course_recording_chat_history": "Chat history recording cannot be enabled when course_recording "
                                                      "is disabled."}
                )
            if self.course_recording_chat_group_history:
                raise ValidationError(
                    {"course_recording_chat_group_history": "Group chat history recording cannot be enabled when "
                                                            "course_recording is disabled."}
                )

        if self.client_side_ai_only and self.ai_external_processing_allowed:
            raise ValidationError(
                {"ai_external_processing_allowed": "External AI processing cannot be enabled when client-side AI only "
                                                   "is active."}
            )

        if self.strict_privacy_mode:
            if self.ai_external_processing_allowed:
                raise ValidationError(
                    {
                        "ai_external_processing_allowed":
                            "External AI processing must be disabled in strict privacy mode."
                    }
                )

    def __str__(self):
        return f"Policy for {self.name}"


class CourseMembership(models.Model):
    course = models.ForeignKey(
        "academy.Course",
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="course_memberships",
    )
    role = models.CharField(max_length=32, choices=core_enums.Role.choices)
    status = models.CharField(max_length=32, choices=core_enums.Status.choices, default=core_enums.Status.ACTIVE)

    can_manage_content = models.BooleanField(default=False)
    can_manage_enrollment = models.BooleanField(default=False)
    can_reply_inbox = models.BooleanField(default=False)
    can_moderate_comments = models.BooleanField(default=False)
    can_grade = models.BooleanField(default=False)

    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("course", "user", "role")
