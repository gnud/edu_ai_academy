from django.contrib import admin

from .models import AIAgent, Course, CoursePolicy, CourseMembership
from .services import save_course


class CoursePolicyInline(admin.StackedInline):
    model = CoursePolicy
    extra = 0


class CourseMembershipInline(admin.TabularInline):
    model = CourseMembership
    extra = 0


@admin.register(AIAgent)
class AIAgentAdmin(admin.ModelAdmin):
    list_display = ("pk", "name", "slug", "is_active", "can_lead_sessions", "can_answer_students", "can_grade", "created_at")
    list_filter = ("is_active", "can_lead_sessions", "can_answer_students", "can_grade")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("pk", "title", "slug", "audience_type", "is_active", "is_published", "enrollment_open", "created_by", "created_at")
    list_filter = ("is_active", "is_published", "enrollment_open", "audience_type")
    search_fields = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}
    exclude = ("created_by",)
    inlines = [CoursePolicyInline, CourseMembershipInline]

    def save_model(self, request, obj, form, change):
        save_course(obj, request.user, change)


@admin.register(CoursePolicy)
class CoursePolicyAdmin(admin.ModelAdmin):
    list_display = ("pk", "name", "course", "is_active", "is_system_default", "course_recording", "strict_privacy_mode")
    list_filter = ("is_active", "is_system_default", "course_recording", "strict_privacy_mode")
    search_fields = ("name",)


@admin.register(CourseMembership)
class CourseMembershipAdmin(admin.ModelAdmin):
    list_display = ("pk", "course", "user", "role", "status", "joined_at")
    list_filter = ("role", "status")
    search_fields = ("course__title", "user__username")
