"""
Tests for GET /api/courses/me/  (enrolled courses for the authenticated user).
"""
import pytest
from django.urls import reverse

from apps.core.enums import Role, SemesterStatus, Status

pytestmark = pytest.mark.django_db

URL = reverse('course-me')


# ── Authentication ─────────────────────────────────────────────────────────────

class TestAuthentication:
    def test_unauthenticated_returns_401(self, client):
        # JWTAuthentication sends WWW-Authenticate: Bearer → DRF returns 401
        res = client.get(URL)
        assert res.status_code == 401

    def test_authenticated_returns_200(self, auth_client):
        res = auth_client.get(URL)
        assert res.status_code == 200


# ── Enrollment isolation ──────────────────────────────────────────────────────

class TestEnrollmentIsolation:
    def test_returns_only_own_enrollments(
        self, auth_client, client, student, other_student,
        make_course, make_semester, make_membership
    ):
        c1 = make_course(title='Mine',   slug='mine')
        c2 = make_course(title='Theirs', slug='theirs')
        s1 = make_semester(c1, name='S1')
        s2 = make_semester(c2, name='S2', status=SemesterStatus.SCHEDULED)
        make_membership(student, s1)
        make_membership(other_student, s2)

        res = auth_client.get(URL)
        assert res.data['pagination']['count'] == 1
        assert res.data['results'][0]['course']['slug'] == 'mine'

    def test_no_enrollments_returns_empty(self, auth_client):
        res = auth_client.get(URL)
        assert res.data['pagination']['count'] == 0

    def test_multiple_enrollments_all_returned(
        self, auth_client, student, make_course, make_semester, make_membership
    ):
        for i in range(3):
            c = make_course(title=f'Course {i}', slug=f'course-me-{i}')
            s = make_semester(c, name=f'Sem {i}', status=SemesterStatus.ACTIVE)
            make_membership(student, s)
        res = auth_client.get(URL)
        assert res.data['pagination']['count'] == 3


# ── Search (?q=) ──────────────────────────────────────────────────────────────

class TestMyCoursesSearch:
    @pytest.fixture(autouse=True)
    def _enroll_student(self, student, make_course, make_semester, make_membership):
        titles = ['Python Basics', 'React Workshop', 'SQL Mastery']
        for i, title in enumerate(titles):
            c = make_course(title=title, slug=f'me-{i}')
            s = make_semester(c, name=f'Sem {i}')
            make_membership(student, s)

    @pytest.mark.parametrize('query,expected_count', [
        ('python',      1),
        ('Python',      1),   # case-insensitive
        ('react',       1),
        ('sql',         1),
        ('workshop',    1),   # substring
        ('nonexistent', 0),
        ('',            3),
    ])
    def test_search_filters_by_course_title(self, auth_client, query, expected_count):
        res = auth_client.get(URL, {'q': query})
        assert res.data['pagination']['count'] == expected_count


# ── Status filter (?status=) ──────────────────────────────────────────────────

class TestMyCoursesStatusFilter:
    @pytest.fixture(autouse=True)
    def _enroll_with_statuses(self, student, make_course, make_semester, make_membership):
        statuses = [Status.ACTIVE, Status.ACTIVE, Status.COMPLETED, Status.DROPPED]
        for i, st in enumerate(statuses):
            c = make_course(title=f'Course {i}', slug=f'status-me-{i}')
            s = make_semester(c, name=f'Sem {i}')
            make_membership(student, s, status=st)

    @pytest.mark.parametrize('status,expected_count', [
        (Status.ACTIVE,    2),
        (Status.COMPLETED, 1),
        (Status.DROPPED,   1),
        (Status.INVITED,   0),
        ('',               4),
    ])
    def test_status_filter(self, auth_client, status, expected_count):
        params = {'status': status} if status else {}
        res = auth_client.get(URL, **({'data': params} if params else {}))
        res = auth_client.get(URL, params)
        assert res.data['pagination']['count'] == expected_count


# ── Response shape ────────────────────────────────────────────────────────────

class TestMyCoursesShape:
    def test_result_fields(self, auth_client, student, make_course, make_semester, make_membership):
        c = make_course(title='Shape Test', slug='shape-test')
        s = make_semester(c)
        make_membership(student, s)
        res = auth_client.get(URL)
        item = res.data['results'][0]
        for field in ('id', 'role', 'status', 'joined_at', 'semester', 'course'):
            assert field in item, f"Missing field: {field}"

    def test_nested_course_has_title(self, auth_client, student, make_course, make_semester, make_membership):
        c = make_course(title='Nested Course', slug='nested-me')
        s = make_semester(c)
        make_membership(student, s)
        res = auth_client.get(URL)
        assert res.data['results'][0]['course']['title'] == 'Nested Course'

    def test_role_is_student_by_default(self, auth_client, student, make_course, make_semester, make_membership):
        c = make_course(title='Role Test', slug='role-test')
        s = make_semester(c)
        make_membership(student, s, role=Role.STUDENT)
        res = auth_client.get(URL)
        assert res.data['results'][0]['role'] == Role.STUDENT


# ── Pagination ─────────────────────────────────────────────────────────────────

class TestMyCoursesPagination:
    def test_pagination_envelope_present(self, auth_client):
        res = auth_client.get(URL)
        assert 'pagination' in res.data
        assert 'results' in res.data

    def test_page_size_respected(
        self, auth_client, student, make_course, make_semester, make_membership
    ):
        for i in range(5):
            c = make_course(title=f'Course {i}', slug=f'pg-{i}')
            s = make_semester(c, name=f'S{i}')
            make_membership(student, s)
        res = auth_client.get(URL, {'page_size': 2})
        assert len(res.data['results']) == 2
        assert res.data['pagination']['count'] == 5