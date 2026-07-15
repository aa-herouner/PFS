"""
URL configuration for poultry_record_system project.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from accounts.views import AppLoginView

urlpatterns = [
    path('admin/', admin.site.urls),
    # Custom login (adds success/failure toasts) must precede auth.urls so it
    # wins the `login` name.
    path('accounts/login/', AppLoginView.as_view(), name='login'),
    # Built-in auth views (logout/password change). Templates + custom
    # user management are fleshed out in Step 2; this provides the URL names
    # (`logout`) the base layout references.
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/', include('accounts.urls')),
    path('', include('core.urls')),
    path('', include('inventory.urls')),
    path('', include('feed.urls')),
    path('', include('health.urls')),
    path('', include('production.urls')),
    path('', include('finance.urls')),
    path('', include('reports.urls')),
    path('', include('dashboard.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
