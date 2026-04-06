"""
URL configuration for RankToRole project.

All application routes are prefixed with /api/v1/.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/translations/', include('translate_app.urls')),
    path('api/v1/resumes/', include('translate_app.resume_urls')),
    path('api/v1/auth/', include('user_app.urls')),
    path('api/v1/contacts/', include('contact_app.urls')),
    path('api/v1/onet/', include('onet_app.urls')),
    # Social auth
    path('', include('social_django.urls', namespace='social')),
]
