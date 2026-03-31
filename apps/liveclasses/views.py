from django.utils import timezone
from django.db.models import Q
from rest_framework import generics, permissions, status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.enums import AttendanceStatus, Role
from apps.academy.models import CourseMembership
from .models import ClassSession, SessionParticipant
from .serializers import (
    ClassSessionDetailSerializer,
    ClassSessionSerializer,
    SessionParticipantSerializer,
)


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
            .select_related('semester__course', 'classroom', 'professor')
            .order_by('starts_at')
        )
        q = self.request.query_params.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(title__icontains=q) |
                Q(semester__course__title__icontains=q)
            )
        status_param = self.request.query_params.get('status', '').strip()
        if status_param:
            qs = qs.filter(status=status_param)

        upcoming = self.request.query_params.get('upcoming', '').strip().lower()
        if upcoming == 'true':
            qs = qs.filter(starts_at__gte=timezone.now())

        return qs


class ClassSessionDetailView(APIView):
    """GET /api/classes/<id>/"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            session = (
                ClassSession.objects
                .select_related('semester__course', 'classroom', 'professor')
                .prefetch_related('participants__user', 'participants__ai_agent')
                .get(pk=pk)
            )
        except ClassSession.DoesNotExist:
            raise NotFound('Session not found.')
        return Response(ClassSessionDetailSerializer(session).data)


class SessionParticipantListView(APIView):
    """
    GET /api/classes/<id>/participants/
    Polled by the classroom UI to get live presence updates.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            session = ClassSession.objects.get(pk=pk)
        except ClassSession.DoesNotExist:
            raise NotFound('Session not found.')
        participants = (
            session.participants
            .select_related('user', 'ai_agent')
            .order_by('role', 'user__last_name', 'user__first_name', 'pk')
        )
        return Response(SessionParticipantSerializer(participants, many=True).data)


class JoinSessionView(APIView):
    """
    POST /api/classes/<id>/join/
    Mark the caller as present. Creates a SessionParticipant if needed,
    deriving role from their CourseMembership (defaults to student).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            session = ClassSession.objects.select_related('semester').get(pk=pk)
        except ClassSession.DoesNotExist:
            raise NotFound('Session not found.')

        # Determine role from course membership.
        membership = (
            CourseMembership.objects
            .filter(semester=session.semester, user=request.user)
            .first()
        )
        role = membership.role if membership else Role.STUDENT

        participant, _ = SessionParticipant.objects.get_or_create(
            session=session,
            user=request.user,
            defaults={'role': role},
        )
        participant.attendance_status = AttendanceStatus.JOINED
        participant.joined_at = timezone.now()
        participant.left_at = None
        participant.save(update_fields=['attendance_status', 'joined_at', 'left_at'])

        return Response(SessionParticipantSerializer(participant).data)


class LeaveSessionView(APIView):
    """POST /api/classes/<id>/leave/"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            participant = SessionParticipant.objects.get(
                session_id=pk, user=request.user,
            )
        except SessionParticipant.DoesNotExist:
            raise NotFound('You are not a participant of this session.')

        participant.attendance_status = AttendanceStatus.LEFT
        participant.left_at = timezone.now()
        participant.save(update_fields=['attendance_status', 'left_at'])

        return Response(status=status.HTTP_204_NO_CONTENT)
