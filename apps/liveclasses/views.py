from django.utils import timezone
from django.db.models import Q
from rest_framework import generics, permissions, status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core.enums import AttendanceStatus, Role
from apps.academy.models import CourseMembership
from apps.communication.models import Thread, ThreadParticipant
from .models import ClassSession, ClassroomGroup, ClassroomGroupMember, SessionParticipant
from django.shortcuts import get_object_or_404
from .serializers import (
    ClassSessionDetailSerializer,
    ClassSessionSerializer,
    ClassroomGroupSerializer,
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


def _get_session_as_professor(pk, user):
    """Return ClassSession or raise 404/403. Only the session professor may proceed."""
    try:
        session = ClassSession.objects.get(pk=pk)
    except ClassSession.DoesNotExist:
        raise NotFound('Session not found.')
    if session.professor_id != user.id:
        raise PermissionDenied('Only the professor can manage groups.')
    return session


class ClassroomGroupListCreateView(APIView):
    """
    GET  /api/classes/<id>/groups/  — list groups for session
    POST /api/classes/<id>/groups/  — create a new group (professor only)
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            session = ClassSession.objects.get(pk=pk)
        except ClassSession.DoesNotExist:
            raise NotFound('Session not found.')
        groups = session.groups.prefetch_related('members__participant__user')
        return Response(ClassroomGroupSerializer(groups, many=True).data)

    def post(self, request, pk):
        session = _get_session_as_professor(pk, request.user)

        name = (request.data.get('name') or '').strip()
        if not name:
            raise ValidationError({'name': 'Group name is required.'})
        participant_ids = request.data.get('participant_ids') or []

        # Resolve participants from this session.
        participants = list(
            SessionParticipant.objects.filter(
                id__in=participant_ids, session=session,
            ).select_related('user')
        )

        # Create a group chat thread with all members + professor.
        user_ids = {p.user_id for p in participants if p.user_id}
        user_ids.add(request.user.id)
        thread = Thread.objects.create(
            thread_type='course',
            subject=f'Group: {name}',
            created_by=request.user,
        )
        for uid in user_ids:
            ThreadParticipant.objects.get_or_create(thread=thread, user_id=uid)

        group = ClassroomGroup.objects.create(session=session, name=name, thread=thread)
        for p in participants:
            ClassroomGroupMember.objects.get_or_create(group=group, participant=p)

        return Response(
            ClassroomGroupSerializer(group).data,
            status=status.HTTP_201_CREATED,
        )


class ClassroomGroupDetailView(APIView):
    """
    PATCH  /api/classes/<pk>/groups/<gid>/  — rename or toggle active (professor only)
    DELETE /api/classes/<pk>/groups/<gid>/  — delete group (professor only)
    """
    permission_classes = [permissions.IsAuthenticated]

    def _get_group(self, pk, gid, user):
        session = _get_session_as_professor(pk, user)
        try:
            return ClassroomGroup.objects.get(pk=gid, session=session)
        except ClassroomGroup.DoesNotExist:
            raise NotFound('Group not found.')

    def patch(self, request, pk, gid):
        group = self._get_group(pk, gid, request.user)
        if 'name' in request.data:
            group.name = (request.data['name'] or '').strip() or group.name
        if 'is_active' in request.data:
            group.is_active = bool(request.data['is_active'])
        group.save()
        return Response(ClassroomGroupSerializer(group).data)

    def delete(self, request, pk, gid):
        group = self._get_group(pk, gid, request.user)
        group.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ClassroomGroupMemberKickView(APIView):
    """
    DELETE /api/classes/<pk>/groups/<gid>/members/<mid>/
    Remove a member from a group (professor only).
    Also removes them from the group's chat thread.
    """
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk, gid, mid):
        _get_session_as_professor(pk, request.user)
        member = get_object_or_404(ClassroomGroupMember, pk=mid, group_id=gid)
        # Remove from group chat thread.
        if member.group.thread_id and member.participant.user_id:
            ThreadParticipant.objects.filter(
                thread_id=member.group.thread_id,
                user_id=member.participant.user_id,
            ).delete()
        member.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SessionGroupingView(APIView):
    """
    PATCH /api/classes/<id>/grouping/  — activate or deactivate grouping mode
    """
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        session = _get_session_as_professor(pk, request.user)
        if 'grouping_active' not in request.data:
            raise ValidationError({'grouping_active': 'Required.'})
        active = bool(request.data['grouping_active'])
        session.grouping_active = active
        session.save(update_fields=['grouping_active'])
        if not active:
            session.groups.all().delete()
        return Response({'grouping_active': session.grouping_active})
