from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from main.views import (
    AuthViewSet,
    ProvinceViewSet,
    RouteViewSet,
    TransportViewSet,
    DriverViewSet,
    PassengerViewSet,
    RideViewSet,
    RatingViewSet,
    DriverDocumentViewSet,
    ChatMessageViewSet,
    LocationViewSet,
)

router = DefaultRouter()
router.register(r'auth', AuthViewSet, basename='auth')
router.register(r'provinces', ProvinceViewSet, basename='province')
router.register(r'routes', RouteViewSet, basename='route')
router.register(r'transports', TransportViewSet, basename='transport')
router.register(r'drivers', DriverViewSet, basename='driver')
router.register(r'passengers', PassengerViewSet, basename='passenger')
router.register(r'rides', RideViewSet, basename='ride')
router.register(r'driver/documents', DriverDocumentViewSet, basename='driverdocument')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/rides/<int:ride_pk>/rating/', RatingViewSet.as_view({'get': 'list', 'post': 'create'}), name='ride-rating'),
    path('api/rides/<int:ride_pk>/messages/', ChatMessageViewSet.as_view({'get': 'list', 'post': 'create'}), name='ride-messages'),
    path('api/rides/<int:ride_pk>/messages/<int:pk>/mark-as-read/', ChatMessageViewSet.as_view({'patch': 'mark_as_read'}), name='message-mark-read'),
    path('api/rides/<int:ride_pk>/messages/unread-count/', ChatMessageViewSet.as_view({'get': 'unread_count'}), name='message-unread-count'),
    path('api/rides/<int:ride_pk>/locations/', LocationViewSet.as_view({'get': 'list', 'post': 'create'}), name='ride-locations'),
    path('api/rides/<int:ride_pk>/locations/latest/', LocationViewSet.as_view({'get': 'latest'}), name='location-latest'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
