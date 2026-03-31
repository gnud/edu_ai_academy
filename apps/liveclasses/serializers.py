from rest_framework import serializers

from .models import ClassSession, Classroom, SessionParticipant

# Deterministic avatar colours — derived from user pk so they never change.
_AVATAR_COLORS = [
    '#3b82f6', '#10b981', '#8b5cf6', '#f59e0b',
    '#ef4444', '#14b8a6', '#f97316', '#ec4899',
]


class ClassroomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Classroom
        fields = ['id', 'name', 'slug']


class SessionParticipantSerializer(serializers.ModelSerializer):
    user_id   = serializers.IntegerField(source='user.id',       read_only=True)
    username  = serializers.CharField(source='user.username',    read_only=True)
    full_name = serializers.SerializerMethodField()
    avatar_color = serializers.SerializerMethodField()

    def get_full_name(self, obj) -> str:
        if obj.user:
            return obj.user.get_full_name() or obj.user.username
        if obj.ai_agent:
            return obj.ai_agent.name
        return 'Unknown'

    def get_avatar_color(self, obj) -> str:
        if obj.user:
            return _AVATAR_COLORS[obj.user.pk % len(_AVATAR_COLORS)]
        return '#6b7280'  # neutral grey for AI

    class Meta:
        model = SessionParticipant
        fields = [
            'id', 'user_id', 'username', 'full_name', 'avatar_color',
            'role', 'attendance_status', 'joined_at', 'left_at',
        ]


class ClassSessionSerializer(serializers.ModelSerializer):
    classroom      = ClassroomSerializer(read_only=True)
    course_title   = serializers.CharField(source='semester.course.title',  read_only=True)
    course_slug    = serializers.CharField(source='semester.course.slug',   read_only=True)
    semester_name  = serializers.CharField(source='semester.name',          read_only=True)
    professor_name = serializers.SerializerMethodField()
    duration_minutes = serializers.SerializerMethodField()

    class Meta:
        model = ClassSession
        fields = [
            'id', 'title', 'description', 'status',
            'starts_at', 'ends_at', 'duration_minutes',
            'classroom',
            'course_title', 'course_slug', 'semester_name',
            'professor_name',
            'created_at',
        ]

    def get_professor_name(self, obj) -> str | None:
        if obj.professor:
            return obj.professor.get_full_name() or obj.professor.username
        return None

    def get_duration_minutes(self, obj) -> int | None:
        if obj.starts_at and obj.ends_at:
            return int((obj.ends_at - obj.starts_at).total_seconds() // 60)
        return None


class AIAgentInfoSerializer(serializers.Serializer):
    id                  = serializers.IntegerField()
    name                = serializers.CharField()
    can_answer_students = serializers.BooleanField()
    can_lead_sessions   = serializers.BooleanField()


class ClassSessionDetailSerializer(ClassSessionSerializer):
    """Full session: participants list + professor user id + AI agent info."""

    professor_id = serializers.IntegerField(source='professor.id', read_only=True)
    participants = serializers.SerializerMethodField()
    ai_agent     = serializers.SerializerMethodField()

    class Meta(ClassSessionSerializer.Meta):
        fields = ClassSessionSerializer.Meta.fields + [
            'professor_id', 'participants', 'ai_agent',
        ]

    def get_participants(self, obj) -> list:
        # Students and professors ordered predictably so seat numbers are stable.
        qs = obj.participants.select_related('user', 'ai_agent').order_by(
            'role', 'user__last_name', 'user__first_name', 'pk',
        )
        return SessionParticipantSerializer(qs, many=True).data

    def get_ai_agent(self, obj) -> dict | None:
        # AI professor presence is tracked as a SessionParticipant with ai_agent set.
        from apps.core.enums import Role
        ai_p = next(
            (p for p in obj.participants.all() if p.ai_agent_id and p.role == Role.PROFESSOR),
            None,
        )
        if ai_p and ai_p.ai_agent:
            return AIAgentInfoSerializer(ai_p.ai_agent).data
        return None
