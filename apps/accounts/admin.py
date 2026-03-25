from django.contrib import admin

from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("pk", "user", "display_name", "is_platform_admin", "is_platform_staff")
    list_filter = ("is_platform_admin", "is_platform_staff")
    search_fields = ("user__username", "display_name")
