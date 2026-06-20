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

rating_list = RatingViewSet.as_view({
    'get': 'list',
    'post': 'create'
})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/rides/<int:ride_pk>/rating/', rating_list, name='ride-rating'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
