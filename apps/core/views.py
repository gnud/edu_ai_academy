from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.academy.models import CourseMembership
from apps.academy.serializers import CourseSerializer, EnrolledCourseSerializer
from apps.liveclasses.models import ClassSession
from apps.liveclasses.serializers import ClassSessionSerializer
from apps.core.enums import SemesterStatus


class HubView(APIView):
    """
    GET /api/hub/
    Dashboard summary for the authenticated student.

    Returns:
      stats            — counts per enrollment/semester status
      upcoming_classes — next 5 class sessions the user is part of
      scheduled        — their scheduled (not-yet-started) course enrollments
      archive          — completed + cancelled enrollments
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        memberships = (
            CourseMembership.objects
            .filter(user=user)
            .select_related('semester', 'semester__course', 'semester__course__created_by')
            .prefetch_related('semester__course__semesters')
        )

        # ── Stats ──────────────────────────────────────────────────────────
        active_memberships    = memberships.filter(semester__status=SemesterStatus.ACTIVE)
        scheduled_memberships = memberships.filter(semester__status=SemesterStatus.SCHEDULED)
        completed_memberships = memberships.filter(semester__status=SemesterStatus.COMPLETED)
        cancelled_memberships = memberships.filter(semester__status=SemesterStatus.CANCELLED)

        stats = {
            'in_the_mix':  active_memberships.count(),
            'on_deck':     scheduled_memberships.count(),
            'graduated':   completed_memberships.count(),
            'dropped':     cancelled_memberships.count(),
        }

        # ── Upcoming classes ───────────────────────────────────────────────
        # Sessions in semesters the user belongs to, starting from now.
        enrolled_semester_ids = memberships.values_list('semester_id', flat=True)
        upcoming_sessions = (
            ClassSession.objects
            .filter(
                semester_id__in=enrolled_semester_ids,
                starts_at__gte=timezone.now(),
            )
            .select_related('semester__course', 'classroom', 'professor')
            .order_by('starts_at')[:5]
        )

        # ── Scheduled courses ──────────────────────────────────────────────
        scheduled = scheduled_memberships.order_by('semester__starts_on')

        # ── Archive ────────────────────────────────────────────────────────
        archived = (
            memberships
            .filter(semester__status__in=[SemesterStatus.COMPLETED, SemesterStatus.CANCELLED])
            .order_by('-semester__ends_on')
        )

        return Response({
            'stats':            stats,
            'upcoming_classes': ClassSessionSerializer(upcoming_sessions, many=True).data,
            'scheduled':        EnrolledCourseSerializer(scheduled, many=True).data,
            'archive':          EnrolledCourseSerializer(archived, many=True).data,
        })