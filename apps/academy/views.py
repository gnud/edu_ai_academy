from django.db.models import Q
from rest_framework import generics, permissions

from .models import Course, CourseMembership
from .serializers import CourseSerializer, CourseDetailSerializer, EnrolledCourseSerializer


class CourseListView(generics.ListAPIView):
    """
    GET /api/courses/
    Public catalog of all active, published courses.

    Query params:
      ?q=<str>          — search title, short_description
      ?audience=<str>   — filter by audience_type
      ?ordering=title   — order results (default: -created_at)
    """
    serializer_class = CourseSerializer
    permission_classes = [permissions.AllowAny]
    ordering = ['-created_at']

    def get_queryset(self):
        qs = (
            Course.objects
            .filter(is_active=True, is_published=True)
            .select_related('created_by')
            .prefetch_related('semesters')
        )
        q = self.request.query_params.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(title__icontains=q) | Q(short_description__icontains=q)
            )
        audience = self.request.query_params.get('audience', '').strip()
        if audience:
            qs = qs.filter(audience_type=audience)
        return qs


class CourseDetailView(generics.RetrieveAPIView):
    """GET /api/courses/<slug>/"""
    serializer_class = CourseDetailSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'
    queryset = (
        Course.objects
        .filter(is_active=True, is_published=True)
        .select_related('created_by')
        .prefetch_related('semesters')
    )


class MyCourseListView(generics.ListAPIView):
    """
    GET /api/courses/me/
    Courses the authenticated user is enrolled in (via CourseMembership).

    Query params:
      ?q=<str>        — search course title
      ?status=<str>   — filter by membership status (active, completed, …)
    """
    serializer_class = EnrolledCourseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = (
            CourseMembership.objects
            .filter(user=self.request.user)
            .select_related('semester', 'semester__course', 'semester__course__created_by')
            .prefetch_related('semester__course__semesters')
            .order_by('-joined_at')
        )
        q = self.request.query_params.get('q', '').strip()
        if q:
            qs = qs.filter(semester__course__title__icontains=q)
        status = self.request.query_params.get('status', '').strip()
        if status:
            qs = qs.filter(status=status)
        return qs