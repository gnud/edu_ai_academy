from rest_framework import serializers

from .models import Course, Semester, CourseMembership


class SemesterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Semester
        fields = [
            'id', 'name', 'status', 'enrollment_open',
            'max_students', 'starts_on', 'ends_on',
        ]


class CourseSerializer(serializers.ModelSerializer):
    """Compact representation used in list endpoints."""
    created_by = serializers.StringRelatedField()
    active_semester = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'id', 'title', 'slug', 'short_description',
            'audience_type', 'is_active', 'is_published',
            'created_by', 'created_at',
            'active_semester',
        ]

    def get_active_semester(self, obj) -> dict | None:
        semester = obj.semesters.filter(status='active').first()
        if semester is None:
            return None
        return SemesterSerializer(semester).data


class CourseDetailSerializer(CourseSerializer):
    """Full representation including all semesters and description."""
    semesters = SemesterSerializer(many=True, read_only=True)

    class Meta:
        model = Course
        fields = [
            'id', 'title', 'slug', 'short_description', 'description',
            'audience_type', 'is_active', 'is_published',
            'created_by', 'created_at', 'updated_at',
            'active_semester', 'semesters',
        ]


class EnrolledCourseSerializer(serializers.ModelSerializer):
    """Course as seen from an enrollment — includes membership meta."""
    course = CourseSerializer(source='semester.course', read_only=True)
    semester = SemesterSerializer(read_only=True)
    role = serializers.CharField()
    status = serializers.CharField()
    joined_at = serializers.DateTimeField()

    class Meta:
        model = CourseMembership
        fields = ['id', 'role', 'status', 'joined_at', 'semester', 'course']