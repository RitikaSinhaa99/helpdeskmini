from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    # Admin panel
    path('admin/', admin.site.urls),

    # Frontend routes
    path('', include(('frontend.urls', 'frontend'), namespace='frontend')),

    # API routes for tickets
    path('api/', include(('tickets.urls', 'tickets'), namespace='tickets')),

    # JWT Authentication endpoints
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
