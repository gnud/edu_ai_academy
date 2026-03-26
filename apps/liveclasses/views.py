from django.db.models import Q
from django.utils import timezone
from rest_framework import generics, permissions

from .models import ClassSession
from .serializers import ClassSessionSerializer


class ClassSessionListView(generics.ListAPIView):
    """
    GET /api/classes/
    List of class sessions across all courses.

    Query params:
      ?q=<str>         — search title, course title
      ?upcoming=true   — only sessions starting from now onwards
      ?status=<str>    — filter by status (scheduled, live, ended, canceled)
      ?ordering=starts_at — sort (default: starts_at)
    """
    serializer_class = ClassSessionSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    ordering = ['starts_at']

    def get_queryset(self):
        qs = (
            ClassSession.objects
            .select_related(
                'semester__course',
                'classroom',
                'professor',
            )
            .order_by('starts_at')
        )
        q = self.request.query_params.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(title__icontains=q) |
                Q(semester__course__title__icontains=q)
            )
        status = self.request.query_params.get('status', '').strip()
        if status:
            qs = qs.filter(status=status)

        upcoming = self.request.query_params.get('upcoming', '').strip().lower()
        if upcoming == 'true':
            qs = qs.filter(starts_at__gte=timezone.now())

        return qs