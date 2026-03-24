from django.contrib import admin

from .models import AssignmentSubmission, SessionAssignment

admin.site.register(SessionAssignment)
admin.site.register(AssignmentSubmission)
