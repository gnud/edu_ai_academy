from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.pagination import StandardPagination
from .models import Thread, ThreadParticipant
from .serializers import (
    MessageCreateSerializer,
    MessageSerializer,
    ParticipantUpdateSerializer,
    ThreadCreateSerializer,
    ThreadDetailSerializer,
    ThreadListSerializer,
)


def get_participant_thread(thread_id: int, user) -> tuple[Thread, ThreadParticipant]:
    """Return (thread, participation) or raise 404 / 403."""
    try:
        thread = Thread.objects.prefetch_related(
            'participants__user', 'messages__sender',
        ).get(pk=thread_id)
    except Thread.DoesNotExist:
        raise NotFound("Thread not found.")
    try:
        participation = thread.participants.get(user=user)
    except ThreadParticipant.DoesNotExist:
        raise PermissionDenied("You are not a participant of this thread.")
    return thread, participation


class ThreadListCreateView(APIView):
    """
    GET  /api/messages/threads/   — list caller's threads (paginated)
    POST /api/messages/threads/   — create a new thread
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Thread.objects.filter(
            participants__user=request.user,
        ).prefetch_related('participants__user', 'messages__sender').distinct()

        folder      = request.query_params.get('folder')
        thread_type = request.query_params.get('type')
        starred     = request.query_params.get('starred')

        if folder:
            qs = qs.filter(participants__user=request.user, participants__folder=folder)
        if thread_type:
            qs = qs.filter(thread_type=thread_type)
        if starred == 'true':
            qs = qs.filter(participants__user=request.user, participants__is_starred=True)

        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = ThreadListSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = ThreadCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        thread = serializer.save()
        out = ThreadDetailSerializer(thread, context={'request': request})
        return Response(out.data, status=status.HTTP_200_OK)


class ThreadDetailView(APIView):
    """
    GET    /api/messages/threads/<id>/   — full thread + messages (marks read)
    DELETE /api/messages/threads/<id>/   — archive thread for this user
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        thread, participation = get_participant_thread(pk, request.user)

        # Watermark all current messages as read.
        participation.last_read_at = timezone.now()
        participation.save(update_fields=['last_read_at'])

        serializer = ThreadDetailSerializer(thread, context={'request': request})
        return Response(serializer.data)

    def delete(self, request, pk):
        _, participation = get_participant_thread(pk, request.user)
        participation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MessageListCreateView(APIView):
    """
    GET  /api/messages/threads/<id>/messages/   — list messages
    POST /api/messages/threads/<id>/messages/   — send a message
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        thread, _ = get_participant_thread(pk, request.user)
        msgs = thread.messages.select_related('sender').all()
        return Response(MessageSerializer(msgs, many=True).data)

    def post(self, request, pk):
        thread, _ = get_participant_thread(pk, request.user)
        serializer = MessageCreateSerializer(
            data=request.data,
            context={'request': request, 'thread': thread},
        )
        serializer.is_valid(raise_exception=True)
        msg = serializer.save()
        return Response(MessageSerializer(msg).data, status=status.HTTP_201_CREATED)


class ParticipantStateView(APIView):
    """
    PATCH /api/messages/threads/<id>/me/   — update folder / star / read watermark
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        _, participation = get_participant_thread(pk, request.user)
        serializer = ParticipantUpdateSerializer(participation, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)