"""
Tests for GET /api/hub/  (dashboard summary).
"""
import datetime

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.core.enums import Role, SemesterStatus, Status

pytestmark = pytest.mark.django_db

URL = reverse('hub')


# ── Authentication ─────────────────────────────────────────────────────────────

class TestHubAuth:
    def test_unauthenticated_returns_401(self, client):
        # JWTAuthentication sends WWW-Authenticate: Bearer → DRF returns 401
        res = client.get(URL)
        assert res.status_code == 401

    def test_authenticated_returns_200(self, auth_client):
        res = auth_client.get(URL)
        assert res.status_code == 200


# ── Response envelope ─────────────────────────────────────────────────────────

class TestHubEnvelope:
    def test_top_level_keys_present(self, auth_client):
        res = auth_client.get(URL)
        for key in ('stats', 'upcoming_classes', 'scheduled', 'archive'):
            assert key in res.data, f"Missing key: {key}"

    def test_stats_keys_present(self, auth_client):
        res = auth_client.get(URL)
        for key in ('in_the_mix', 'on_deck', 'graduated', 'dropped'):
            assert key in res.data['stats'], f"Missing stats key: {key}"

    def test_empty_user_returns_zero_stats(self, auth_client):
        res = auth_client.get(URL)
        stats = res.data['stats']
        assert stats == {'in_the_mix': 0, 'on_deck': 0, 'graduated': 0, 'dropped': 0}

    def test_empty_user_returns_empty_lists(self, auth_client):
        res = auth_client.get(URL)
        assert res.data['upcoming_classes'] == []
        assert res.data['scheduled'] == []
        assert res.data['archive'] == []


# ── Stats counts ──────────────────────────────────────────────────────────────

class TestHubStats:
    @pytest.mark.parametrize('semester_statuses,expected_stats', [
        (
            [SemesterStatus.ACTIVE],
            {'in_the_mix': 1, 'on_deck': 0, 'graduated': 0, 'dropped': 0},
        ),
        (
            [SemesterStatus.ACTIVE, SemesterStatus.ACTIVE],
            {'in_the_mix': 2, 'on_deck': 0, 'graduated': 0, 'dropped': 0},
        ),
        (
            [SemesterStatus.SCHEDULED],
            {'in_the_mix': 0, 'on_deck': 1, 'graduated': 0, 'dropped': 0},
        ),
        (
            [SemesterStatus.COMPLETED],
            {'in_the_mix': 0, 'on_deck': 0, 'graduated': 1, 'dropped': 0},
        ),
        (
            [SemesterStatus.CANCELLED],
            {'in_the_mix': 0, 'on_deck': 0, 'graduated': 0, 'dropped': 1},
        ),
        (
            [SemesterStatus.ACTIVE, SemesterStatus.SCHEDULED, SemesterStatus.COMPLETED, SemesterStatus.CANCELLED],
            {'in_the_mix': 1, 'on_deck': 1, 'graduated': 1, 'dropped': 1},
        ),
    ])
    def test_stats_match_membership_statuses(
        self,
        auth_client, student,
        make_course, make_semester, make_membership,
        semester_statuses, expected_stats,
    ):
        for i, sem_status in enumerate(semester_statuses):
            c = make_course(title=f'Course {i}', slug=f'hub-stats-{i}')
            s = make_semester(c, name=f'Sem {i}', status=sem_status)
            make_membership(student, s)

        res = auth_client.get(URL)
        assert res.data['stats'] == expected_stats


# ── Stats isolation (other user's memberships not counted) ────────────────────

class TestHubStatsIsolation:
    def test_other_users_memberships_not_counted(
        self, auth_client, other_student,
        make_course, make_semester, make_membership,
    ):
        c = make_course(title='Other Course', slug='other-hub')
        s = make_semester(c)
        make_membership(other_student, s)

        res = auth_client.get(URL)
        stats = res.data['stats']
        assert all(v == 0 for v in stats.values())


# ── Upcoming classes ──────────────────────────────────────────────────────────

class TestHubUpcomingClasses:
    def test_upcoming_classes_only_from_enrolled_semesters(
        self,
        auth_client, client, student, other_student,
        make_course, make_semester, make_membership, make_session, classroom,
    ):
        now = timezone.now()
        # Student's course → session should appear
        c1 = make_course(title='My Course',    slug='hub-my')
        s1 = make_semester(c1, name='S1')
        make_membership(student, s1)
        make_session(s1, classroom, title='My Session', starts_at=now + datetime.timedelta(hours=1))

        # Other student's course → session should NOT appear
        c2 = make_course(title='Their Course', slug='hub-their')
        s2 = make_semester(c2, name='S2')
        make_membership(other_student, s2)
        make_session(s2, classroom, title='Their Session', starts_at=now + datetime.timedelta(hours=2))

        res = auth_client.get(URL)
        titles = [sess['title'] for sess in res.data['upcoming_classes']]
        assert 'My Session'    in titles
        assert 'Their Session' not in titles

    def test_past_sessions_excluded_from_upcoming(
        self, auth_client, student,
        make_course, make_semester, make_membership, make_session, classroom,
    ):
        now = timezone.now()
        c = make_course(title='Past Course', slug='hub-past')
        s = make_semester(c)
        make_membership(student, s)
        make_session(s, classroom, title='Past', starts_at=now - datetime.timedelta(hours=1))
        make_session(s, classroom, title='Future', starts_at=now + datetime.timedelta(hours=1))

        res = auth_client.get(URL)
        titles = [sess['title'] for sess in res.data['upcoming_classes']]
        assert 'Future' in titles
        assert 'Past'   not in titles

    def test_upcoming_capped_at_5(
        self, auth_client, student,
        make_course, make_semester, make_membership, make_session, classroom,
    ):
        now = timezone.now()
        c = make_course(title='Big Course', slug='hub-big')
        s = make_semester(c)
        make_membership(student, s)
        for i in range(8):
            make_session(s, classroom, title=f'S{i}', starts_at=now + datetime.timedelta(hours=i + 1))

        res = auth_client.get(URL)
        assert len(res.data['upcoming_classes']) == 5


# ── Scheduled / Archive sections ──────────────────────────────────────────────

class TestHubSections:
    @pytest.mark.parametrize('sem_status,section,expected_count', [
        (SemesterStatus.SCHEDULED,  'scheduled', 1),
        (SemesterStatus.COMPLETED,  'archive',   1),
        (SemesterStatus.CANCELLED,  'archive',   1),
        (SemesterStatus.ACTIVE,     'scheduled', 0),
        (SemesterStatus.ACTIVE,     'archive',   0),
    ])
    def test_enrollment_appears_in_correct_section(
        self, auth_client, student,
        make_course, make_semester, make_membership,
        sem_status, section, expected_count,
    ):
        c = make_course(title='Section Course', slug=f'hub-sec-{sem_status}')
        s = make_semester(c, name='Sem', status=sem_status)
        make_membership(student, s)

        res = auth_client.get(URL)
        assert len(res.data[section]) == expected_count

    def test_archive_contains_both_completed_and_cancelled(
        self, auth_client, student,
        make_course, make_semester, make_membership,
    ):
        for i, st in enumerate([SemesterStatus.COMPLETED, SemesterStatus.CANCELLED]):
            c = make_course(title=f'Archive {i}', slug=f'hub-arc-{i}')
            s = make_semester(c, name=f'S{i}', status=st)
            make_membership(student, s)

        res = auth_client.get(URL)
        assert len(res.data['archive']) == 2