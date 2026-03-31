from django.db import models
from django.utils import timezone
from rest_framework import serializers

from .models import Message, Thread, ThreadParticipant


class SenderSerializer(serializers.Serializer):
    id        = serializers.IntegerField()
    username  = serializers.CharField()
    full_name = serializers.SerializerMethodField()
    role      = serializers.SerializerMethodField()

    def get_full_name(self, obj) -> str:
        return obj.get_full_name() or obj.username

    def get_role(self, obj) -> str | None:
        if obj.is_superuser or obj.is_staff:
            return 'admin'
        groups = {g.name for g in obj.groups.all()}
        if 'professor' in groups:
            return 'professor'
        if 'support' in groups:
            return 'support'
        return None


class MessageSerializer(serializers.ModelSerializer):
    sender = SenderSerializer(read_only=True)

    class Meta:
        model = Message
        fields = [
            'id', 'sender', 'body', 'message_type',
            'metadata', 'sent_at',
        ]


class ThreadParticipantSerializer(serializers.ModelSerializer):
    user_id  = serializers.IntegerField(source='user.id',       read_only=True)
    username = serializers.CharField(source='user.username',     read_only=True)
    full_name = serializers.SerializerMethodField()

    def get_full_name(self, obj) -> str:
        return obj.user.get_full_name() or obj.user.username

    class Meta:
        model = ThreadParticipant
        fields = ['user_id', 'username', 'full_name', 'folder', 'is_starred', 'last_read_at']


class ThreadListSerializer(serializers.ModelSerializer):
    """Compact thread representation for the inbox list."""
    participants = ThreadParticipantSerializer(many=True, read_only=True)
    message_count  = serializers.SerializerMethodField()
    unread_count   = serializers.SerializerMethodField()
    last_message   = serializers.SerializerMethodField()
    # Caller's own participation state (folder, star, read watermark)
    my_state       = serializers.SerializerMethodField()

    def get_message_count(self, obj) -> int:
        return obj.messages.count()

    def get_unread_count(self, obj) -> int:
        request = self.context.get('request')
        if not request:
            return 0
        try:
            p = obj.participants.get(user=request.user)
        except ThreadParticipant.DoesNotExist:
            return 0
        if p.last_read_at is None:
            return obj.messages.count()
        return obj.messages.filter(sent_at__gt=p.last_read_at).count()

    def get_last_message(self, obj) -> dict | None:
        msg = obj.messages.last()
        if msg is None:
            return None
        return {
            'body_preview': msg.body[:120],
            'sent_at':      msg.sent_at,
            'sender':       msg.sender.username if msg.sender else None,
        }

    def get_my_state(self, obj) -> dict | None:
        request = self.context.get('request')
        if not request:
            return None
        try:
            p = obj.participants.get(user=request.user)
            return ThreadParticipantSerializer(p).data
        except ThreadParticipant.DoesNotExist:
            return None

    class Meta:
        model = Thread
        fields = [
            'id', 'thread_type', 'subject', 'course',
            'last_message_at', 'created_at',
            'participants', 'message_count', 'unread_count',
            'last_message', 'my_state',
        ]


class ThreadDetailSerializer(ThreadListSerializer):
    """Full thread with all messages."""
    messages = MessageSerializer(many=True, read_only=True)

    class Meta(ThreadListSerializer.Meta):
        fields = ThreadListSerializer.Meta.fields + ['messages']


class ThreadCreateSerializer(serializers.ModelSerializer):
    participant_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        default=list,
    )

    class Meta:
        model = Thread
        fields = ['thread_type', 'subject', 'course', 'participant_ids']

    def create(self, validated_data):
        participant_ids = validated_data.pop('participant_ids', [])
        request = self.context['request']
        user_ids = set(participant_ids) | {request.user.id}

        # For PM threads, reuse an existing thread between the exact same participants.
        if validated_data.get('thread_type') == 'pm':
            existing = (
                Thread.objects.filter(thread_type='pm')
                .annotate(pcount=models.Count('participants'))
                .filter(pcount=len(user_ids))
            )
            for uid in user_ids:
                existing = existing.filter(participants__user_id=uid)
            thread = existing.first()
            if thread:
                return thread

        thread = Thread.objects.create(
            created_by=request.user,
            **validated_data,
        )

        # Always add the creator as a participant.
        for uid in user_ids:
            ThreadParticipant.objects.get_or_create(thread=thread, user_id=uid)

        return thread


class MessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['body', 'metadata']

    def create(self, validated_data):
        thread  = self.context['thread']
        request = self.context['request']
        now     = timezone.now()

        msg = Message.objects.create(
            thread=thread,
            sender=request.user,
            message_type=thread.thread_type,
            **validated_data,
        )

        # Bump the thread's last_message_at.
        thread.last_message_at = now
        thread.save(update_fields=['last_message_at'])

        # Mark sender as having read up to now.
        ThreadParticipant.objects.filter(
            thread=thread, user=request.user,
        ).update(last_read_at=now)

        return msg


class ParticipantUpdateSerializer(serializers.ModelSerializer):
    """PATCH /threads/<id>/me/ — update caller's own participation state."""

    class Meta:
        model = ThreadParticipant
        fields = ['folder', 'is_starred', 'last_read_at']
        extra_kwargs = {field: {'required': False} for field in fields}