from django.contrib import admin

from .models import StudentGroup, StudentGroupMember, SessionAssignment, AssignmentSubmission


class StudentGroupMemberInline(admin.TabularInline):
    model = StudentGroupMember
    extra = 0


class AssignmentSubmissionInline(admin.TabularInline):
    model = AssignmentSubmission
    extra = 0


@admin.register(StudentGroup)
class StudentGroupAdmin(admin.ModelAdmin):
    list_display = ("pk", "name", "session", "group_type", "assignment_mode_enabled", "created_by", "created_at")
    list_filter = ("group_type", "assignment_mode_enabled")
    search_fields = ("name",)
    inlines = [StudentGroupMemberInline]


@admin.register(StudentGroupMember)
class StudentGroupMemberAdmin(admin.ModelAdmin):
    list_display = ("pk", "group", "user", "ai_agent", "role")
    list_filter = ("role",)


@admin.register(SessionAssignment)
class SessionAssignmentAdmin(admin.ModelAdmin):
    list_display = ("pk", "title", "session", "student_group", "due_at", "created_by", "created_at")
    search_fields = ("title",)
    inlines = [AssignmentSubmissionInline]


@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
    list_display = ("pk", "assignment", "student_group", "submitted_by", "submission_type", "submitted_at")
    list_filter = ("submission_type",)
