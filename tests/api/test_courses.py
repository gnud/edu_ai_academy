"""
Tests for GET /api/courses/  (catalog) and GET /api/courses/<slug>/  (detail).
"""
import pytest
from django.urls import reverse

from apps.core.enums import AudienceType, SemesterStatus

pytestmark = pytest.mark.django_db


# ── Helpers ───────────────────────────────────────────────────────────────────

LIST_URL = reverse('course-list')


def detail_url(slug):
    return reverse('course-detail', kwargs={'slug': slug})


def get_list(client, **params):
    return client.get(LIST_URL, params)


# ── Pagination envelope ───────────────────────────────────────────────────────

class TestPaginationEnvelope:
    def test_returns_pagination_and_results_keys(self, client, course):
        res = client.get(LIST_URL)
        assert res.status_code == 200
        assert 'pagination' in res.data
        assert 'results' in res.data

    def test_pagination_fields_present(self, client, course):
        res = client.get(LIST_URL)
        p = res.data['pagination']
        for field in ('count', 'page', 'page_size', 'pages', 'next', 'previous'):
            assert field in p, f"Missing pagination field: {field}"

    def test_default_page_size_is_10(self, client, make_course):
        for i in range(12):
            make_course(title=f'Course {i}', slug=f'course-{i}')
        res = client.get(LIST_URL)
        assert len(res.data['results']) == 10
        assert res.data['pagination']['count'] == 12

    def test_custom_page_size(self, client, make_course):
        for i in range(5):
            make_course(title=f'Course {i}', slug=f'course-{i}')
        res = client.get(LIST_URL, {'page_size': 2})
        assert len(res.data['results']) == 2

    def test_page_2_returns_remaining_items(self, client, make_course):
        for i in range(3):
            make_course(title=f'Course {i}', slug=f'course-{i}')
        res = client.get(LIST_URL, {'page': 2, 'page_size': 2})
        assert len(res.data['results']) == 1


# ── Visibility filtering ──────────────────────────────────────────────────────

class TestCourseVisibility:
    @pytest.mark.parametrize('is_active,is_published,expected_count', [
        (True,  True,  1),   # visible
        (False, True,  0),   # inactive → hidden
        (True,  False, 0),   # unpublished → hidden
        (False, False, 0),   # both off → hidden
    ])
    def test_only_active_and_published_courses_appear(
        self, client, make_course, is_active, is_published, expected_count
    ):
        make_course(title='Visible?', slug='visible', is_active=is_active, is_published=is_published)
        res = get_list(client)
        assert res.data['pagination']['count'] == expected_count

    def test_multiple_courses_count_correctly(self, client, make_course):
        make_course(title='A', slug='a')
        make_course(title='B', slug='b')
        make_course(title='C', slug='c', is_published=False)
        res = get_list(client)
        assert res.data['pagination']['count'] == 2


# ── Search (?q=) ──────────────────────────────────────────────────────────────

class TestCourseSearch:
    @pytest.fixture(autouse=True)
    def _setup(self, make_course):
        make_course(title='Python Fundamentals', slug='python', short_description='Learn Python')
        make_course(title='React Mastery',       slug='react',  short_description='Build UIs with React')
        make_course(title='Data Science 101',    slug='data',   short_description='Intro to pandas')

    @pytest.mark.parametrize('query,expected_count', [
        ('python',       1),
        ('Python',       1),   # case-insensitive
        ('react',        1),
        ('pandas',       1),   # matches short_description
        ('Learn',        1),   # matches short_description
        ('101',          1),
        ('nonexistent',  0),
        ('',             3),   # empty → all
    ])
    def test_search_by_title_and_short_description(self, client, query, expected_count):
        res = get_list(client, q=query)
        assert res.data['pagination']['count'] == expected_count, (
            f"q={query!r}: expected {expected_count}, got {res.data['pagination']['count']}"
        )


# ── Audience filter ───────────────────────────────────────────────────────────

class TestAudienceFilter:
    @pytest.fixture(autouse=True)
    def _setup(self, make_course):
        make_course(title='For Students', slug='students', audience_type=AudienceType.ADULTS_ONLY)
        make_course(title='For Teachers', slug='teachers', audience_type=AudienceType.CHILDREN_ONLY)
        make_course(title='For Everyone', slug='everyone', audience_type=AudienceType.MIXED)

    @pytest.mark.parametrize('audience,expected_count', [
        (AudienceType.ADULTS_ONLY,   1),
        (AudienceType.CHILDREN_ONLY, 1),
        (AudienceType.MIXED,         1),
        ('',                         3),   # no filter → all
    ])
    def test_audience_filter(self, client, audience, expected_count):
        params = {'audience': audience} if audience else {}
        res = get_list(client, **params)
        assert res.data['pagination']['count'] == expected_count


# ── Response shape ────────────────────────────────────────────────────────────

class TestCourseListShape:
    def test_result_contains_expected_fields(self, client, course):
        res = get_list(client)
        item = res.data['results'][0]
        for field in ('id', 'title', 'slug', 'short_description', 'audience_type',
                      'is_active', 'is_published', 'created_by', 'created_at', 'active_semester'):
            assert field in item, f"Missing field: {field}"

    def test_active_semester_is_none_when_absent(self, client, course):
        res = get_list(client)
        assert res.data['results'][0]['active_semester'] is None

    def test_active_semester_populated_when_present(self, client, course, active_semester):
        res = get_list(client)
        sem = res.data['results'][0]['active_semester']
        assert sem is not None
        assert sem['id'] == active_semester.pk
        assert sem['status'] == SemesterStatus.ACTIVE


# ── Detail endpoint ───────────────────────────────────────────────────────────

class TestCourseDetail:
    def test_returns_200_for_existing_slug(self, client, course):
        res = client.get(detail_url(course.slug))
        assert res.status_code == 200

    def test_returns_404_for_unknown_slug(self, client):
        res = client.get(detail_url('does-not-exist'))
        assert res.status_code == 404

    @pytest.mark.parametrize('is_active,is_published', [
        (False, True),
        (True,  False),
        (False, False),
    ])
    def test_returns_404_for_hidden_course(self, client, make_course, is_active, is_published):
        c = make_course(slug='hidden', is_active=is_active, is_published=is_published)
        res = client.get(detail_url(c.slug))
        assert res.status_code == 404

    def test_detail_includes_description_and_semesters(self, client, course, active_semester):
        res = client.get(detail_url(course.slug))
        assert 'description' in res.data
        assert 'semesters' in res.data
        assert len(res.data['semesters']) == 1

    def test_detail_slug_matches(self, client, course):
        res = client.get(detail_url(course.slug))
        assert res.data['slug'] == course.slug