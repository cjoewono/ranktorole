import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture(autouse=True)
def disable_throttling(db, monkeypatch):
    from django.core.cache import cache
    from user_app.views import LoginRateThrottle
    cache.clear()
    monkeypatch.setattr(LoginRateThrottle, "allow_request", lambda self, request, view: True)


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email='test@example.com',
        username='testuser',
        password='strongpassword123',
    )


REGISTER_URL = '/api/v1/auth/register/'
LOGIN_URL = '/api/v1/auth/login/'
REFRESH_URL = '/api/v1/auth/refresh/'
LOGOUT_URL = '/api/v1/auth/logout/'
PROFILE_URL = '/api/v1/auth/profile/'


class TestRegister:
    def test_register_valid(self, client, db):
        resp = client.post(REGISTER_URL, {
            'email': 'new@example.com',
            'username': 'newuser',
            'password': 'strongpassword123',
        })
        assert resp.status_code == 201
        assert 'access' in resp.data
        assert 'refresh_token' in resp.cookies

    def test_register_response_excludes_password(self, client, db):
        resp = client.post(REGISTER_URL, {
            'email': 'new@example.com',
            'username': 'newuser',
            'password': 'strongpassword123',
        })
        assert 'password' not in resp.data
        assert 'password' not in resp.data.get('user', {})

    def test_register_duplicate_email(self, client, user):
        resp = client.post(REGISTER_URL, {
            'email': 'test@example.com',
            'username': 'other',
            'password': 'strongpassword123',
        })
        assert resp.status_code == 400

    def test_register_missing_password(self, client, db):
        resp = client.post(REGISTER_URL, {'email': 'only@example.com', 'username': 'only'})
        assert resp.status_code == 400

    def test_register_missing_email(self, client, db):
        resp = client.post(REGISTER_URL, {'username': 'only', 'password': 'strongpassword123'})
        assert resp.status_code == 400

    def test_register_invalid_email_format(self, client, db):
        resp = client.post(REGISTER_URL, {
            'email': 'not-an-email',
            'username': 'baduser',
            'password': 'strongpassword123',
        })
        assert resp.status_code == 400


class TestLogin:
    def test_login_valid(self, client, user):
        resp = client.post(LOGIN_URL, {
            'email': 'test@example.com',
            'password': 'strongpassword123',
        })
        assert resp.status_code == 200
        assert 'access' in resp.data
        assert 'refresh_token' in resp.cookies

    def test_login_response_excludes_password(self, client, user):
        resp = client.post(LOGIN_URL, {
            'email': 'test@example.com',
            'password': 'strongpassword123',
        })
        assert 'password' not in resp.data
        assert 'password' not in resp.data.get('user', {})

    def test_login_wrong_password(self, client, user):
        resp = client.post(LOGIN_URL, {
            'email': 'test@example.com',
            'password': 'wrongpassword',
        })
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client, db):
        resp = client.post(LOGIN_URL, {
            'email': 'nobody@example.com',
            'password': 'somepassword',
        })
        assert resp.status_code == 401

    def test_login_missing_email(self, client, db):
        resp = client.post(LOGIN_URL, {'password': 'somepassword'})
        assert resp.status_code == 401


class TestTokenRefresh:
    def _login_and_get_refresh(self, client, user):
        resp = client.post(LOGIN_URL, {
            'email': 'test@example.com',
            'password': 'strongpassword123',
        })
        return resp.cookies['refresh_token'].value

    def test_refresh_valid_cookie(self, client, user):
        refresh = self._login_and_get_refresh(client, user)
        client.cookies['refresh_token'] = refresh
        resp = client.post(REFRESH_URL)
        assert resp.status_code == 200
        assert 'access' in resp.data

    def test_refresh_valid_body(self, client, user):
        refresh = self._login_and_get_refresh(client, user)
        resp = client.post(REFRESH_URL, {'refresh': refresh})
        assert resp.status_code == 200
        assert 'access' in resp.data

    def test_refresh_invalid_token(self, client, db):
        resp = client.post(REFRESH_URL, {'refresh': 'invalid.token.value'})
        assert resp.status_code == 401

    def test_refresh_missing_token(self, client, db):
        resp = client.post(REFRESH_URL)
        assert resp.status_code == 400

    def test_refresh_blacklisted_token(self, client, user):
        refresh = self._login_and_get_refresh(client, user)
        # Blacklist via logout
        client.cookies['refresh_token'] = refresh
        client.post(LOGOUT_URL)
        # Attempt refresh with blacklisted token
        resp = client.post(REFRESH_URL, {'refresh': refresh})
        assert resp.status_code == 401


class TestLogout:
    def test_logout_clears_cookie(self, client, user):
        resp_login = client.post(LOGIN_URL, {
            'email': 'test@example.com',
            'password': 'strongpassword123',
        })
        client.cookies['refresh_token'] = resp_login.cookies['refresh_token'].value
        resp = client.post(LOGOUT_URL)
        assert resp.status_code == 200
        # Cookie should be cleared (max_age=0 or deleted)
        assert resp.cookies.get('refresh_token', {}).get('max-age') in (0, '', None) or \
               resp.cookies.get('refresh_token', {}).value in ('', None)

    def test_logout_without_token_still_succeeds(self, client, db):
        resp = client.post(LOGOUT_URL)
        assert resp.status_code == 200


class TestProtectedEndpoint:
    def test_with_valid_token(self, client, user):
        resp_login = client.post(LOGIN_URL, {
            'email': 'test@example.com',
            'password': 'strongpassword123',
        })
        access = resp_login.data['access']
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        resp = client.get('/api/v1/contacts/')
        assert resp.status_code != 401

    def test_without_token(self, client, db):
        resp = client.get('/api/v1/contacts/')
        assert resp.status_code == 401

    def test_with_invalid_token(self, client, db):
        client.credentials(HTTP_AUTHORIZATION='Bearer invalid.token.here')
        resp = client.get('/api/v1/contacts/')
        assert resp.status_code == 401


class TestProfile:
    def test_patch_profile_context(self, client, user):
        resp = client.post(LOGIN_URL, {
            'email': 'test@example.com',
            'password': 'strongpassword123',
        })
        access = resp.data['access']
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

        profile_data = {
            'profile_context': {
                'branch': 'Navy',
                'mos': 'IT',
                'target_sector': 'Technology',
                'skills': ['Cross-functional leadership', 'Agile', 'Cloud infrastructure']
            }
        }
        resp = client.patch(PROFILE_URL, profile_data, format='json')
        assert resp.status_code == 200
        assert resp.data['profile_context']['branch'] == 'Navy'

    def test_profile_context_returned_on_login(self, client, user):
        user.profile_context = {'branch': 'Army', 'mos': 'Infantry'}
        user.save()
        resp = client.post(LOGIN_URL, {
            'email': 'test@example.com',
            'password': 'strongpassword123',
        })
        assert resp.status_code == 200
        assert resp.data['user']['profile_context']['branch'] == 'Army'

    def test_patch_requires_auth(self, client, db):
        resp = client.patch(PROFILE_URL, {'profile_context': {}}, format='json')
        assert resp.status_code == 401

    def test_profile_context_null_by_default(self, client, user):
        resp = client.post(LOGIN_URL, {
            'email': 'test@example.com',
            'password': 'strongpassword123',
        })
        assert resp.data['user']['profile_context'] is None

    def test_get_profile(self, client, user):
        resp = client.post(LOGIN_URL, {
            'email': 'test@example.com',
            'password': 'strongpassword123',
        })
        access = resp.data['access']
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        resp = client.get(PROFILE_URL)
        assert resp.status_code == 200
        assert resp.data['email'] == 'test@example.com'
