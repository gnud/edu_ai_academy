from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet
from django.shortcuts import get_object_or_404, redirect
from django.urls import path

from apps.core.enums import SemesterStatus
from .models import AIAgent, Course, CoursePolicy, CourseMembership, Semester
from .services import save_course, save_semester, toggle_course_published, toggle_course_active

CREATE_ONLY_STATUSES = [
    (SemesterStatus.SCHEDULED, SemesterStatus.SCHEDULED.label),
    (SemesterStatus.ACTIVE, SemesterStatus.ACTIVE.label),
]


class SemesterInlineForm(forms.ModelForm):
    class Meta:
        model = Semester
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields["status"].choices = CREATE_ONLY_STATUSES


class SemesterInlineFormset(BaseInlineFormSet):
    """
    Validates overlaps and active-uniqueness between sibling semester forms
    in the same submission — including when all are new (course_id not yet set).
    """

    def clean(self):
        super().clean()

        active_count = 0
        semesters = []

        for form in self.forms:
            if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                continue
            status = form.cleaned_data.get("status")
            starts_on = form.cleaned_data.get("starts_on")
            ends_on = form.cleaned_data.get("ends_on")
            if not status or not starts_on:
                continue
            if ends_on and ends_on <= starts_on:
                form.add_error("ends_on", "End date must be after start date.")
                continue
            if status in (SemesterStatus.ACTIVE, SemesterStatus.SCHEDULED):
                semesters.append((starts_on, ends_on, status, form))
            if status == SemesterStatus.ACTIVE:
                active_count += 1

        if active_count > 1:
            raise ValidationError("Only one active semester is allowed per course at a time.")

        for i, (s1, e1, _, _) in enumerate(semesters):
            for j, (s2, e2, _, form2) in enumerate(semesters):
                if j <= i:
                    continue
                no_conflict = (
                    (e1 is not None and e1 < s2) or
                    (e2 is not None and e2 < s1)
                )
                if not no_conflict:
                    form2.add_error(
                        "starts_on",
                        "This semester's dates overlap with another semester in this form.",
                    )
                    break


class CoursePolicyInline(admin.StackedInline):
    model = CoursePolicy
    extra = 0


class SemesterInline(admin.TabularInline):
    model = Semester
    form = SemesterInlineForm
    formset = SemesterInlineFormset
    extra = 0
    show_change_link = True
    can_delete = False


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
    list_display = ("pk", "title", "slug", "audience_type", "is_active", "is_published", "created_by", "created_at")
    list_filter = ("is_active", "is_published", "audience_type")
    search_fields = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}
    exclude = ("created_by",)
    inlines = [CoursePolicyInline, SemesterInline]
    change_form_template = "admin/academy/course/change_form.html"

    def save_model(self, request, obj, form, change):
        save_course(obj, request.user, change)

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("<int:pk>/toggle-publish/", self.admin_site.admin_view(self.toggle_publish_view), name="academy_course_toggle_publish"),
            path("<int:pk>/toggle-active/", self.admin_site.admin_view(self.toggle_active_view), name="academy_course_toggle_active"),
        ]
        return custom + urls

    def toggle_publish_view(self, request, pk):
        course = get_object_or_404(Course, pk=pk)
        toggle_course_published(course)
        if course.is_published:
            self.message_user(request, f'"{course}" has been published.', messages.SUCCESS)
        else:
            self.message_user(request, f'"{course}" has been unpublished.', messages.ERROR)
        return redirect("admin:academy_course_change", pk)

    def toggle_active_view(self, request, pk):
        course = get_object_or_404(Course, pk=pk)
        toggle_course_active(course)
        if course.is_active:
            self.message_user(request, f'"{course}" has been activated.', messages.SUCCESS)
        else:
            self.message_user(request, f'"{course}" has been deactivated.', messages.ERROR)
        return redirect("admin:academy_course_change", pk)


@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = ("pk", "name", "course", "status", "enrollment_open", "max_students", "starts_on", "ends_on")
    list_filter = ("status", "enrollment_open")
    search_fields = ("name", "course__title")
    inlines = [CourseMembershipInline]

    def save_model(self, request, obj, form, change):
        save_semester(obj)


@admin.register(CoursePolicy)
class CoursePolicyAdmin(admin.ModelAdmin):
    list_display = ("pk", "name", "course", "is_active", "is_system_default", "course_recording", "strict_privacy_mode")
    list_filter = ("is_active", "is_system_default", "course_recording", "strict_privacy_mode")
    search_fields = ("name",)


@admin.register(CourseMembership)
class CourseMembershipAdmin(admin.ModelAdmin):
    list_display = ("pk", "semester", "user", "role", "status", "joined_at")
    list_filter = ("role", "status")
    search_fields = ("semester__name", "semester__course__title", "user__username")
