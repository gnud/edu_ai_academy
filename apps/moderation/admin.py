from django.contrib import admin

from .models import CourseThread, CourseMessage, Report


class CourseMessageInline(admin.TabularInline):
    model = CourseMessage
    extra = 0


@admin.register(CourseThread)
class CourseThreadAdmin(admin.ModelAdmin):
    list_display = ("pk", "subject", "course", "thread_type", "is_closed", "created_by", "created_at")
    list_filter = ("thread_type", "is_closed")
    search_fields = ("subject",)
    inlines = [CourseMessageInline]


@admin.register(CourseMessage)
class CourseMessageAdmin(admin.ModelAdmin):
    list_display = ("pk", "thread", "author", "created_at")
    search_fields = ("body",)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("pk", "report_type", "target_id", "status", "reported_by", "assigned_admin", "created_at", "resolved_at")
    list_filter = ("report_type", "status")
    search_fields = ("reason",)
