"""
Tests for JWT authentication endpoints and token-based access to protected resources.

  POST /api/auth/token/          — obtain access + refresh tokens
  POST /api/auth/token/refresh/  — exchange refresh token for new access token
  POST /api/auth/token/verify/   — check whether a token is valid
"""
import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db

OBTAIN_URL  = reverse('token-obtain')
REFRESH_URL = reverse('token-refresh')
VERIFY_URL  = reverse('token-verify')
HUB_URL     = reverse('hub')
ME_URL      = reverse('course-me')


# ── Helpers ───────────────────────────────────────────────────────────────────

def obtain_tokens(client, username, password):
    res = client.post(OBTAIN_URL, {'username': username, 'password': password}, format='json')
    return res


# ── Token obtain ──────────────────────────────────────────────────────────────

class TestTokenObtain:
    def test_valid_credentials_return_200(self, client, student):
        res = obtain_tokens(client, 'student', 'pass')
        assert res.status_code == 200

    def test_response_contains_access_and_refresh(self, client, student):
        res = obtain_tokens(client, 'student', 'pass')
        assert 'access'  in res.data
        assert 'refresh' in res.data

    def test_tokens_are_non_empty_strings(self, client, student):
        res = obtain_tokens(client, 'student', 'pass')
        assert isinstance(res.data['access'],  str) and len(res.data['access'])  > 0
        assert isinstance(res.data['refresh'], str) and len(res.data['refresh']) > 0

    @pytest.mark.parametrize('username,password,expected_status', [
        ('student',      'wrongpassword', 401),
        ('nonexistent',  'pass',          401),
        ('student',      '',              400),
        ('',             'pass',          400),
        ('',             '',              400),
    ])
    def test_invalid_credentials(self, client, student, username, password, expected_status):
        res = obtain_tokens(client, username, password)
        assert res.status_code == expected_status


# ── Token refresh ─────────────────────────────────────────────────────────────

class TestTokenRefresh:
    def test_valid_refresh_token_returns_new_access(self, client, student):
        tokens = obtain_tokens(client, 'student', 'pass').data
        res = client.post(REFRESH_URL, {'refresh': tokens['refresh']}, format='json')
        assert res.status_code == 200
        assert 'access' in res.data

    def test_new_access_token_differs_from_original(self, client, student):
        tokens = obtain_tokens(client, 'student', 'pass').data
        res = client.post(REFRESH_URL, {'refresh': tokens['refresh']}, format='json')
        # ROTATE_REFRESH_TOKENS=True → new refresh issued too
        assert res.data['access'] != tokens['access']

    @pytest.mark.parametrize('payload,expected_status', [
        ({'refresh': 'not.a.valid.token'},  401),
        ({'refresh': ''},                   400),
        ({},                                400),
    ])
    def test_invalid_refresh_token(self, client, payload, expected_status):
        res = client.post(REFRESH_URL, payload, format='json')
        assert res.status_code == expected_status


# ── Token verify ──────────────────────────────────────────────────────────────

class TestTokenVerify:
    def test_valid_access_token_returns_200(self, client, student):
        tokens = obtain_tokens(client, 'student', 'pass').data
        res = client.post(VERIFY_URL, {'token': tokens['access']}, format='json')
        assert res.status_code == 200

    def test_valid_refresh_token_also_verifies(self, client, student):
        tokens = obtain_tokens(client, 'student', 'pass').data
        res = client.post(VERIFY_URL, {'token': tokens['refresh']}, format='json')
        assert res.status_code == 200

    @pytest.mark.parametrize('payload,expected_status', [
        ({'token': 'invalid.token.here'},  401),
        ({'token': ''},                    400),
        ({},                               400),
    ])
    def test_invalid_token(self, client, payload, expected_status):
        res = client.post(VERIFY_URL, payload, format='json')
        assert res.status_code == expected_status


# ── Accessing protected endpoints with JWT ────────────────────────────────────

class TestJWTProtectedAccess:
    def test_bearer_token_grants_access_to_hub(self, client, student):
        tokens = obtain_tokens(client, 'student', 'pass').data
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        res = client.get(HUB_URL)
        assert res.status_code == 200

    def test_bearer_token_grants_access_to_courses_me(self, client, student):
        tokens = obtain_tokens(client, 'student', 'pass').data
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        res = client.get(ME_URL)
        assert res.status_code == 200

    def test_no_token_returns_401(self, client, student):
        res = client.get(HUB_URL)
        assert res.status_code == 401

    @pytest.mark.parametrize('auth_header', [
        'Bearer invalid.token',
        'Bearer ',
        'Token sometoken',       # wrong scheme
        'Basic dXNlcjpwYXNz',   # wrong auth type
    ])
    def test_malformed_or_wrong_scheme_returns_401(self, client, student, auth_header):
        client.credentials(HTTP_AUTHORIZATION=auth_header)
        res = client.get(HUB_URL)
        assert res.status_code == 401

    def test_refreshed_token_grants_access(self, client, student):
        tokens = obtain_tokens(client, 'student', 'pass').data
        refresh_res = client.post(REFRESH_URL, {'refresh': tokens['refresh']}, format='json')
        new_access = refresh_res.data['access']
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {new_access}')
        res = client.get(HUB_URL)
        assert res.status_code == 200