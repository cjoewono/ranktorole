from django.urls import path

from .views import (
    GoogleCallbackView,
    GoogleOAuthRedirectView,
    LoginView,
    LogoutView,
    RegisterView,
    TokenRefreshView,
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='auth-register'),
    path('login/', LoginView.as_view(), name='auth-login'),
    path('refresh/', TokenRefreshView.as_view(), name='auth-refresh'),
    path('logout/', LogoutView.as_view(), name='auth-logout'),
    path('google/', GoogleOAuthRedirectView.as_view(), name='auth-google'),
    path('google/callback/', GoogleCallbackView.as_view(), name='auth-google-callback'),
]
