from rest_framework import serializers

from .models import ClassSession, Classroom


class ClassroomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Classroom
        fields = ['id', 'name', 'slug']


class ClassSessionSerializer(serializers.ModelSerializer):
    classroom = ClassroomSerializer(read_only=True)
    course_title = serializers.CharField(source='semester.course.title', read_only=True)
    course_slug = serializers.CharField(source='semester.course.slug', read_only=True)
    semester_name = serializers.CharField(source='semester.name', read_only=True)
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
            delta = obj.ends_at - obj.starts_at
            return int(delta.total_seconds() // 60)
        return None