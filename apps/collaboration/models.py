from django.db import models

from apps.core import enums as core_enums


class StudentGroup(models.Model):
    session = models.ForeignKey(
        "liveclasses.ClassSession",
        on_delete=models.CASCADE,
        related_name="student_groups",
    )
    name = models.CharField(max_length=255)
    group_type = models.CharField(
        max_length=20,
        choices=core_enums.GroupType.choices,
        default=core_enums.GroupType.TEAM
    )

    created_by = models.ForeignKey(
        "auth.User",
        on_delete=models.PROTECT,
        related_name="created_student_groups",
    )

    assignment_mode_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class StudentGroupMember(models.Model):
    group = models.ForeignKey(
        "collaboration.StudentGroup",
        on_delete=models.CASCADE,
        related_name="members",
    )
    user = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="student_group_memberships",
    )
    ai_agent = models.ForeignKey(
        "academy.AIAgent",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="student_group_memberships",
    )
    role = models.CharField(max_length=32, choices=core_enums.Role.choices)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(user__isnull=False, ai_agent__isnull=True) |
                    models.Q(user__isnull=True, ai_agent__isnull=False)
                ),
                name="student_group_member_user_xor_ai_agent",
            )
        ]


class SessionAssignment(models.Model):
    session = models.ForeignKey(
        "liveclasses.ClassSession",
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    student_group = models.ForeignKey(
        "collaboration.StudentGroup",
        on_delete=models.CASCADE,
        related_name="assignments",
        null=True,
        blank=True,
    )

    title = models.CharField(max_length=255)
    instructions = models.TextField(blank=True)
    due_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        "auth.User",
        on_delete=models.PROTECT,
        related_name="created_session_assignments",
    )

    created_at = models.DateTimeField(auto_now_add=True)


class AssignmentSubmission(models.Model):
    assignment = models.ForeignKey(
        "collaboration.SessionAssignment",
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    student_group = models.ForeignKey(
        "collaboration.StudentGroup",
        on_delete=models.CASCADE,
        related_name="submissions",
    )

    submitted_by = models.ForeignKey(
        "auth.User",
        on_delete=models.PROTECT,
        related_name="assignment_submissions",
    )

    submission_type = models.CharField(max_length=20, choices=core_enums.SubmissionType.choices)
    text_content = models.TextField(blank=True)
    external_url = models.URLField(blank=True)
    file = models.FileField(upload_to="assignment_submissions/", blank=True, null=True)

    submitted_at = models.DateTimeField(auto_now_add=True)
