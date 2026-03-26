"""
Tests for GET /api/classes/  (class sessions list).
"""
import datetime

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.core.enums import ClassSessionStatus

pytestmark = pytest.mark.django_db

URL = reverse('class-session-list')


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def semester_with_sessions(make_course, make_semester, make_session, classroom):
    course = make_course(title='Live Course', slug='live-course')
    sem = make_semester(course, name='Live Sem')
    now = timezone.now()
    s1 = make_session(sem, classroom, title='Intro Session',   starts_at=now - datetime.timedelta(hours=2))
    s2 = make_session(sem, classroom, title='Python Workshop', starts_at=now + datetime.timedelta(hours=1))
    s3 = make_session(sem, classroom, title='SQL Lab',         starts_at=now + datetime.timedelta(days=2))
    return sem, [s1, s2, s3]


# ── Basic access ──────────────────────────────────────────────────────────────

class TestClassSessionAccess:
    def test_unauthenticated_can_list(self, client, semester_with_sessions):
        res = client.get(URL)
        assert res.status_code == 200

    def test_returns_pagination_envelope(self, client, semester_with_sessions):
        res = client.get(URL)
        assert 'pagination' in res.data
        assert 'results' in res.data

    def test_returns_all_sessions(self, client, semester_with_sessions):
        _, sessions = semester_with_sessions
        res = client.get(URL)
        assert res.data['pagination']['count'] == len(sessions)


# ── Search (?q=) ──────────────────────────────────────────────────────────────

class TestClassSessionSearch:
    @pytest.fixture(autouse=True)
    def _setup(self, make_course, make_semester, make_session, classroom):
        self.course = make_course(title='Django Deep Dive', slug='django-deep-dive')
        self.sem = make_semester(self.course, name='Spring')
        now = timezone.now()
        make_session(self.sem, classroom, title='Intro to Django',   starts_at=now)
        make_session(self.sem, classroom, title='ORM Workshop',      starts_at=now + datetime.timedelta(hours=1))
        make_session(self.sem, classroom, title='REST Framework Lab', starts_at=now + datetime.timedelta(hours=2))

    @pytest.mark.parametrize('query,expected_count', [
        ('django',   3),   # "Django Deep Dive" is the course title → all 3 sessions match
        ('Django',   3),   # case-insensitive
        ('orm',      1),
        ('lab',      1),
        ('rest',     1),
        ('deep',     3),   # "Django Deep Dive" → all 3 sessions match via course title
        ('xyz',      0),
        ('',         3),
    ])
    def test_search(self, client, query, expected_count):
        res = client.get(URL, {'q': query})
        assert res.data['pagination']['count'] == expected_count, (
            f"q={query!r}: expected {expected_count}, got {res.data['pagination']['count']}"
        )


# ── Upcoming filter (?upcoming=true) ─────────────────────────────────────────

class TestUpcomingFilter:
    @pytest.fixture(autouse=True)
    def _setup(self, make_course, make_semester, make_session, classroom):
        course = make_course(title='Upcoming Course', slug='upcoming-course')
        sem = make_semester(course, name='Sem')
        now = timezone.now()
        make_session(sem, classroom, title='Past Session',    starts_at=now - datetime.timedelta(hours=3))
        make_session(sem, classroom, title='Future Session 1', starts_at=now + datetime.timedelta(hours=1))
        make_session(sem, classroom, title='Future Session 2', starts_at=now + datetime.timedelta(days=1))

    @pytest.mark.parametrize('param,expected_count', [
        ('true',  2),
        ('false', 3),   # no filter applied when not "true"
        ('',      3),
    ])
    def test_upcoming_param(self, client, param, expected_count):
        params = {'upcoming': param} if param else {}
        res = client.get(URL, params)
        assert res.data['pagination']['count'] == expected_count


# ── Status filter (?status=) ─────────────────────────────────────────────────

class TestStatusFilter:
    @pytest.fixture(autouse=True)
    def _setup(self, make_course, make_semester, make_session, classroom):
        course = make_course(title='Status Course', slug='status-course')
        sem = make_semester(course, name='Sem')
        now = timezone.now()
        statuses = [
            ClassSessionStatus.SCHEDULED,
            ClassSessionStatus.SCHEDULED,
            ClassSessionStatus.LIVE,
            ClassSessionStatus.ENDED,
            ClassSessionStatus.CANCELED,
        ]
        for i, st in enumerate(statuses):
            make_session(
                sem, classroom,
                title=f'Session {i}',
                status=st,
                starts_at=now + datetime.timedelta(hours=i),
            )

    @pytest.mark.parametrize('status,expected_count', [
        (ClassSessionStatus.SCHEDULED, 2),
        (ClassSessionStatus.LIVE,      1),
        (ClassSessionStatus.ENDED,     1),
        (ClassSessionStatus.CANCELED,  1),
        ('',                           5),
    ])
    def test_status_filter(self, client, status, expected_count):
        params = {'status': status} if status else {}
        res = client.get(URL, params)
        assert res.data['pagination']['count'] == expected_count


# ── Response shape ────────────────────────────────────────────────────────────

class TestClassSessionShape:
    def test_result_fields(self, client, semester_with_sessions):
        res = client.get(URL)
        item = res.data['results'][0]
        for field in (
            'id', 'title', 'description', 'status',
            'starts_at', 'ends_at', 'duration_minutes',
            'classroom', 'course_title', 'course_slug',
            'semester_name', 'professor_name', 'created_at',
        ):
            assert field in item, f"Missing field: {field}"

    def test_duration_minutes_computed(self, client, semester_with_sessions):
        res = client.get(URL)
        # make_session creates 1-hour sessions
        assert res.data['results'][0]['duration_minutes'] == 60

    def test_course_title_denormalised(self, client, semester_with_sessions):
        res = client.get(URL)
        assert res.data['results'][0]['course_title'] == 'Live Course'


# ── Pagination ─────────────────────────────────────────────────────────────────

class TestClassSessionPagination:
    def test_page_size_respected(self, client, make_course, make_semester, make_session, classroom):
        course = make_course(title='Paged Course', slug='paged-course')
        sem = make_semester(course, name='Sem')
        now = timezone.now()
        for i in range(5):
            make_session(sem, classroom, title=f'S{i}', starts_at=now + datetime.timedelta(hours=i))
        res = client.get(URL, {'page_size': 2})
        assert len(res.data['results']) == 2
        assert res.data['pagination']['count'] == 5