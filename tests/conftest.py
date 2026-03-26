"""
Shared pytest fixtures for the AI Academy test suite.

All DB fixtures use Django's test database and are function-scoped by default.
Use `db` or `django_db` marker to opt in per test/module.
"""
import datetime

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from apps.academy.models import AIAgent, Course, CourseMembership, CoursePolicy, Semester
from apps.core.enums import AudienceType, Role, SemesterStatus, Status
from apps.liveclasses.models import ClassSession, Classroom


# ── HTTP clients ─────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def student(db):
    return User.objects.create_user(
        username='student', password='pass', first_name='Jane', last_name='Student'
    )


@pytest.fixture
def other_student(db):
    return User.objects.create_user(username='other_student', password='pass')


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(
        username='staff', password='pass', is_staff=True
    )


@pytest.fixture
def auth_client(client, student):
    client.force_authenticate(user=student)
    return client


# ── Courses ───────────────────────────────────────────────────────────────────

@pytest.fixture
def make_course(db, staff_user):
    """Factory: create a course with sensible defaults."""
    def _make(
        title='Test Course',
        slug=None,
        is_active=True,
        is_published=True,
        audience_type=AudienceType.MIXED,
        description='A test course.',
        short_description='Short desc.',
    ):
        return Course.objects.create(
            title=title,
            slug=slug or title.lower().replace(' ', '-'),
            is_active=is_active,
            is_published=is_published,
            audience_type=audience_type,
            description=description,
            short_description=short_description,
            created_by=staff_user,
        )
    return _make


@pytest.fixture
def course(make_course):
    return make_course(title='Python Basics', slug='python-basics')


@pytest.fixture
def make_semester(db):
    """Factory: create a semester for a course."""
    def _make(
        course,
        name='Spring 2025',
        status=SemesterStatus.ACTIVE,
        starts_on=None,
        ends_on=None,
        enrollment_open=True,
        max_students=None,
    ):
        today = datetime.date.today()
        return Semester.objects.create(
            course=course,
            name=name,
            status=status,
            starts_on=starts_on or today - datetime.timedelta(days=30),
            ends_on=ends_on,
            enrollment_open=enrollment_open,
            max_students=max_students,
        )
    return _make


@pytest.fixture
def active_semester(make_semester, course):
    return make_semester(course=course, name='Active Semester', status=SemesterStatus.ACTIVE)


@pytest.fixture
def make_membership(db):
    """Factory: enroll a user in a semester."""
    def _make(user, semester, role=Role.STUDENT, status=Status.ACTIVE):
        return CourseMembership.objects.create(
            user=user, semester=semester, role=role, status=status
        )
    return _make


# ── Classrooms & sessions ─────────────────────────────────────────────────────

@pytest.fixture
def classroom(db):
    return Classroom.objects.create(name='Room 101', slug='room-101')


@pytest.fixture
def make_session(db, staff_user):
    """Factory: create a class session."""
    def _make(
        semester,
        classroom,
        title='Session 1',
        status='scheduled',
        starts_at=None,
        ends_at=None,
    ):
        now = datetime.datetime(2025, 6, 1, 10, 0, tzinfo=datetime.timezone.utc)
        return ClassSession.objects.create(
            semester=semester,
            classroom=classroom,
            title=title,
            status=status,
            starts_at=starts_at or now,
            ends_at=ends_at or (starts_at or now) + datetime.timedelta(hours=1),
            created_by=staff_user,
        )
    return _make