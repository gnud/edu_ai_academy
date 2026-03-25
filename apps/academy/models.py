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


class Semester(models.Model):
    course = models.ForeignKey(
        "academy.Course",
        on_delete=models.CASCADE,
        related_name="semesters",
    )
    name = models.CharField(max_length=255)
    max_students = models.PositiveIntegerField(null=True, blank=True)
    starts_on = models.DateField()
    ends_on = models.DateField(null=True, blank=True)
    enrollment_open = models.BooleanField(default=True)
    status = models.CharField(
        max_length=20,
        choices=core_enums.SemesterStatus.choices,
        default=core_enums.SemesterStatus.SCHEDULED,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        from django.db.models import Q

        if self.ends_on and self.starts_on and self.ends_on <= self.starts_on:
            raise ValidationError(
                {"ends_on": "End date must be after start date."}
            )

        # Course not yet saved (e.g. inline on new Course form) — skip DB checks.
        if not self.course_id:
            return

        if self.status == core_enums.SemesterStatus.ACTIVE:
            qs = Semester.objects.filter(
                course=self.course,
                status=core_enums.SemesterStatus.ACTIVE,
            )
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError(
                    {"status": "A course can only have one active semester at a time."}
                )

        if self.status in (
            core_enums.SemesterStatus.ACTIVE,
            core_enums.SemesterStatus.SCHEDULED,
        ):
            qs = Semester.objects.filter(
                course=self.course,
                status__in=[
                    core_enums.SemesterStatus.ACTIVE,
                    core_enums.SemesterStatus.SCHEDULED,
                ],
            )
            if self.pk:
                qs = qs.exclude(pk=self.pk)

            # Non-overlapping: other ends before self starts, OR self ends before other starts.
            # ends_on is nullable (open-ended), so only apply each condition when the relevant
            # end date exists.
            no_conflict = Q(ends_on__isnull=False, ends_on__lt=self.starts_on)
            if self.ends_on:
                no_conflict |= Q(starts_on__gt=self.ends_on)

            if qs.exclude(no_conflict).exists():
                raise ValidationError(
                    {"starts_on": "This semester's dates overlap with an existing active or scheduled semester."}
                )

    def __str__(self):
        return f"{self.course} — {self.name}"


class CourseMembership(models.Model):
    semester = models.ForeignKey(
        "academy.Semester",
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
        unique_together = ("semester", "user", "role")
