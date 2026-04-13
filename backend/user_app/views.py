import logging
import secrets
from urllib.parse import urlencode

import requests as http_requests
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import LoginSerializer, RegisterSerializer, UserSerializer

User = get_user_model()
logger = logging.getLogger(__name__)

GOOGLE_AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
GOOGLE_USERINFO_URL = 'https://www.googleapis.com/oauth2/v3/userinfo'


class LoginRateThrottle(AnonRateThrottle):
    scope = 'login'


class RegisterThrottle(AnonRateThrottle):
    scope = 'register'


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        'refresh_token',
        refresh_token,
        max_age=7 * 24 * 60 * 60,
        httponly=True,
        secure=not settings.DEBUG,
        samesite='Lax',
    )


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [RegisterThrottle]

    def post(self, request: 'Request') -> Response:
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Registration failed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        response = Response(
            {
                'user': UserSerializer(user).data,
                'access': str(refresh.access_token),
            },
            status=status.HTTP_201_CREATED,
        )
        _set_refresh_cookie(response, str(refresh))
        return response


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request: 'Request') -> Response:
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning('Failed login attempt for email: %s', request.data.get('email', ''))
            return Response(
                {"error": "Invalid email or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        response = Response(
            {
                'user': UserSerializer(user).data,
                'access': str(refresh.access_token),
            }
        )
        _set_refresh_cookie(response, str(refresh))
        return response


class TokenRefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        raw_refresh = request.COOKIES.get('refresh_token') or request.data.get('refresh')
        if not raw_refresh:
            return Response(
                {'detail': 'Refresh token required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            refresh = RefreshToken(raw_refresh)
            new_access = str(refresh.access_token)
            response = Response({'access': new_access})
            # ROTATE_REFRESH_TOKENS=True means the token object already rotated;
            # write the (same or new) refresh value back to the cookie.
            _set_refresh_cookie(response, str(refresh))
            return response
        except TokenError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        raw_refresh = request.COOKIES.get('refresh_token') or request.data.get('refresh')
        if raw_refresh:
            try:
                RefreshToken(raw_refresh).blacklist()
            except TokenError:
                pass
        response = Response({'detail': 'Logged out.'})
        response.delete_cookie('refresh_token')
        return response


class GoogleOAuthRedirectView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        state = secrets.token_urlsafe(32)
        request.session['google_oauth_state'] = state
        params = {
            'client_id': settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY,
            'redirect_uri': settings.GOOGLE_OAUTH_REDIRECT_URI,
            'response_type': 'code',
            'scope': 'openid email profile',
            'access_type': 'offline',
            'prompt': 'select_account',
            'state': state,
        }
        auth_url = f'{GOOGLE_AUTH_URL}?{urlencode(params)}'
        return Response({'auth_url': auth_url})


class GoogleCallbackView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        code = request.data.get('code')
        state = request.data.get('state')

        if not code:
            return Response(
                {'detail': 'code is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate state parameter to prevent CSRF
        saved_state = request.session.pop('google_oauth_state', None)
        if not saved_state or saved_state != state:
            return Response(
                {'detail': 'Invalid or missing state parameter.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Exchange authorization code for Google tokens
        token_resp = http_requests.post(
            GOOGLE_TOKEN_URL,
            data={
                'code': code,
                'client_id': settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY,
                'client_secret': settings.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET,
                'redirect_uri': settings.GOOGLE_OAUTH_REDIRECT_URI,
                'grant_type': 'authorization_code',
            },
            timeout=10,
        )
        if not token_resp.ok:
            logger.warning('Google token exchange failed: %s', token_resp.text)
            return Response(
                {'detail': 'Failed to exchange code with Google.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        google_access_token = token_resp.json().get('access_token')

        # Retrieve user info from Google
        userinfo_resp = http_requests.get(
            GOOGLE_USERINFO_URL,
            headers={'Authorization': f'Bearer {google_access_token}'},
            timeout=10,
        )
        if not userinfo_resp.ok:
            return Response(
                {'detail': 'Failed to retrieve user info from Google.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        userinfo = userinfo_resp.json()
        email = userinfo.get('email')
        if not email:
            return Response(
                {'detail': 'Google account has no email address.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = _get_or_create_google_user(email, userinfo)
        refresh = RefreshToken.for_user(user)
        response = Response(
            {
                'user': UserSerializer(user).data,
                'access': str(refresh.access_token),
            },
            status=status.HTTP_200_OK,
        )
        _set_refresh_cookie(response, str(refresh))
        return response


class ProfileView(APIView):
    """
    GET   /api/v1/auth/profile/ — return authenticated user data.
    PATCH /api/v1/auth/profile/ — update authenticated user's profile_context.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)


def _get_or_create_google_user(email: str, userinfo: dict) -> User:
    try:
        return User.objects.get(email=email)
    except User.DoesNotExist:
        pass

    base = email.split('@')[0]
    username = base
    counter = 1
    while User.objects.filter(username=username).exists():
        username = f'{base}{counter}'
        counter += 1

    return User.objects.create_user(
        email=email,
        username=username,
        first_name=userinfo.get('given_name', ''),
        last_name=userinfo.get('family_name', ''),
        password=None,
    )
