from django.contrib import admin

from .models import Classroom, ClassSession, SessionParticipant


class SessionParticipantInline(admin.TabularInline):
    model = SessionParticipant
    extra = 0


@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ("pk", "name", "slug", "created_at")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(ClassSession)
class ClassSessionAdmin(admin.ModelAdmin):
    list_display = ("pk", "title", "semester", "classroom", "status", "professor", "starts_at", "ends_at")
    list_filter = ("status",)
    search_fields = ("title", "semester__name", "semester__course__title")
    inlines = [SessionParticipantInline]


@admin.register(SessionParticipant)
class SessionParticipantAdmin(admin.ModelAdmin):
    list_display = ("pk", "session", "user", "ai_agent", "role", "attendance_status", "joined_at")
    list_filter = ("role", "attendance_status")
