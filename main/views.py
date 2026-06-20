from django.db.models import Q, Sum, F, Avg
from django.utils import timezone

from rest_framework import status, viewsets, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import User, Province, Route, Transport, DriverProfile, PassengerProfile, Ride, Rating, DriverDocument
from .serializers import (
    ProvinceSerializer,
    RouteSerializer,
    TransportSerializer,
    DriverProfileSerializer,
    PassengerProfileSerializer,
    RideSerializer,
    RatingSerializer,
    DriverDocumentSerializer,
)
from .auth_serializers import (
    RegisterPassengerSerializer,
    RegisterDriverSerializer,
    LoginSerializer,
    ChangePasswordSerializer,
    RideSearchSerializer,
)
from .permissions import IsDriver, IsPassenger, IsRideParticipant


class AuthViewSet(viewsets.GenericViewSet):
    permission_classes = [AllowAny]

    def _get_tokens_for_user(self, user):
        refresh = RefreshToken.for_user(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user_id': user.id,
            'username': user.username,
            'role': user.role,
        }

    @extend_schema(request=RegisterPassengerSerializer, responses=RegisterPassengerSerializer)
    @action(detail=False, methods=['post'], url_path='register/passenger')
    def register_passenger(self, request):
        s = RegisterPassengerSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = s.save()
        return Response(self._get_tokens_for_user(user), status=status.HTTP_201_CREATED)

    @extend_schema(request=RegisterDriverSerializer, responses=RegisterDriverSerializer)
    @action(detail=False, methods=['post'], url_path='register/driver')
    def register_driver(self, request):
        s = RegisterDriverSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = s.save()
        return Response(self._get_tokens_for_user(user), status=status.HTTP_201_CREATED)

    @extend_schema(request=LoginSerializer, responses=LoginSerializer)
    @action(detail=False, methods=['post'])
    def login(self, request):
        s = LoginSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = s.validated_data['user']
        return Response(self._get_tokens_for_user(user))

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def logout(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"detail": "Refresh token required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'detail': 'Logged out.'}, status=status.HTTP_204_NO_CONTENT)
        except Exception:
            return Response({"detail": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(request=ChangePasswordSerializer)
    @action(detail=False, methods=['post'], url_path='change-password',
            permission_classes=[IsAuthenticated])
    def change_password(self, request):
        s = ChangePasswordSerializer(data=request.data, context={'request': request})
        s.is_valid(raise_exception=True)
        s.save()
        return Response({'detail': 'Password changed.'})


class ProvinceViewSet(viewsets.ModelViewSet):
    queryset           = Province.objects.all().order_by('name')
    serializer_class   = ProvinceSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [AllowAny()]
        return [IsAdminUser()]


class RouteViewSet(viewsets.ModelViewSet):
    serializer_class = RouteSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(name='province', description='Filter by province ID', required=False, type=OpenApiTypes.INT),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        qs          = Route.objects.all().order_by('name')
        province_id = self.request.query_params.get('province')
        if province_id:
            qs = qs.filter(province_id=province_id)
        return qs

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [AllowAny()]
        return [IsAdminUser()]


class TransportViewSet(viewsets.GenericViewSet,
                       mixins.ListModelMixin,
                       mixins.RetrieveModelMixin):
    serializer_class = TransportSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(name='from_province', description='Filter by from province ID', required=False, type=OpenApiTypes.INT),
            OpenApiParameter(name='to_province', description='Filter by to province ID', required=False, type=OpenApiTypes.INT),
            OpenApiParameter(name='type', description='Filter by type (ORDINARY, COMFORT, LUXURY)', required=False, type=OpenApiTypes.STR),
            OpenApiParameter(name='route', description='Filter by route ID', required=False, type=OpenApiTypes.INT),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        qs     = Transport.objects.all()
        params = self.request.query_params
        if params.get('from_province'):
            qs = qs.filter(from_province_id=params['from_province'])
        if params.get('to_province'):
            qs = qs.filter(to_province_id=params['to_province'])
        if params.get('type'):
            qs = qs.filter(type=params['type'])
        if params.get('route'):
            qs = qs.filter(route_id=params['route'])
        return qs

    def get_permissions(self):
        if self.action == 'me':
            return [IsAuthenticated(), IsDriver()]
        return [AllowAny()]

    @action(detail=False, methods=['get', 'put', 'patch'])
    def me(self, request):
        try:
            transport = Transport.objects.get(driver=request.user)
        except Transport.DoesNotExist:
            return Response({'detail': 'No transport registered.'}, status=status.HTTP_404_NOT_FOUND)

        if request.method == 'GET':
            return Response(TransportSerializer(transport).data)

        data = {**request.data, 'driver': request.user.id}
        s = TransportSerializer(transport, data=data, partial=(request.method == 'PATCH'))
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)


class DriverViewSet(viewsets.GenericViewSet,
                    mixins.ListModelMixin,
                    mixins.RetrieveModelMixin):
    serializer_class = DriverProfileSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(name='from_province', description='Filter by from province ID', required=False, type=OpenApiTypes.INT),
            OpenApiParameter(name='to_province', description='Filter by to province ID', required=False, type=OpenApiTypes.INT),
            OpenApiParameter(name='min_rating', description='Filter by minimum rating', required=False, type=OpenApiTypes.FLOAT),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        qs     = DriverProfile.objects.all().order_by('-avg_rating')
        params = self.request.query_params
        if params.get('from_province'):
            qs = qs.filter(driver__transport_info__from_province_id=params['from_province'])
        if params.get('to_province'):
            qs = qs.filter(driver__transport_info__to_province_id=params['to_province'])
        if params.get('min_rating'):
            qs = qs.filter(avg_rating__gte=params['min_rating'])
        return qs

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [AllowAny()]
        return [IsAuthenticated(), IsDriver()]

    @action(detail=False, methods=['get', 'patch'])
    def me(self, request):
        profile = request.user.driver_profile

        if request.method == 'GET':
            return Response(DriverProfileSerializer(profile).data)

        safe = {k: v for k, v in request.data.items()
                if k not in ('avg_rating', 'total_trips', 'joining_date', 'driver')}
        s = DriverProfileSerializer(profile, data=safe, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        rides = Ride.objects.filter(driver=request.user)
        return Response({
            'total_rides':    rides.count(),
            'completed':      rides.filter(status=Ride.Status.COMPLETED).count(),
            'cancelled':      rides.filter(status=Ride.Status.CANCELLED).count(),
            'pending':        rides.filter(status=Ride.Status.PENDING).count(),
            'in_progress':    rides.filter(status=Ride.Status.IN_PROGRESS).count(),
            'total_earnings': rides.filter(
                                  status=Ride.Status.COMPLETED,
                                  payment_status=Ride.PaymentStatus.PAID,
                              ).aggregate(total=Sum('price'))['total'] or 0,
            'rides_today':    rides.filter(created_at__date=timezone.now().date()).count(),
            'avg_rating':     getattr(getattr(request.user, 'driver_profile', None), 'avg_rating', 0.0),
        })

    @action(detail=False, methods=['get'])
    def active(self, request):
        rides = Ride.objects.filter(
            driver=request.user,
            status__in=[Ride.Status.PENDING, Ride.Status.CONFIRMED, Ride.Status.IN_PROGRESS],
        ).order_by('departure_time')
        return Response(RideSerializer(rides, many=True).data)


class PassengerViewSet(viewsets.GenericViewSet):
    serializer_class   = PassengerProfileSerializer
    permission_classes = [IsAuthenticated, IsPassenger]

    @action(detail=False, methods=['get', 'patch'])
    def me(self, request):
        profile = request.user.passenger_profile

        if request.method == 'GET':
            return Response(PassengerProfileSerializer(profile).data)

        safe = {k: v for k, v in request.data.items()
                if k not in ('total_trips', 'joining_date', 'passenger')}
        s = PassengerProfileSerializer(profile, data=safe, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        rides = Ride.objects.filter(passenger=request.user)
        return Response({
            'total_rides': rides.count(),
            'completed':   rides.filter(status=Ride.Status.COMPLETED).count(),
            'cancelled':   rides.filter(status=Ride.Status.CANCELLED).count(),
            'total_spent': rides.filter(
                               status=Ride.Status.COMPLETED,
                               payment_status=Ride.PaymentStatus.PAID,
                           ).aggregate(total=Sum('price'))['total'] or 0,
        })


class RideViewSet(viewsets.GenericViewSet,
                  mixins.ListModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.CreateModelMixin):
    serializer_class = RideSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(name='status', description='Filter by status (pending, confirmed, in_progress, completed, cancelled)', required=False, type=OpenApiTypes.STR),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_permissions(self):
        if self.action == 'search':
            return [AllowAny()]
        if self.action == 'create':
            return [IsAuthenticated(), IsPassenger()]
        if self.action in ('update_status', 'payment'):
            return [IsAuthenticated(), IsDriver()]
        if self.action == 'cancel':
            return [IsAuthenticated(), IsPassenger()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user   = self.request.user
        status_filter = self.request.query_params.get('status')
        qs = Ride.objects.filter(Q(driver=user) | Q(passenger=user)).order_by('-created_at')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    def create(self, request, *args, **kwargs):
        s = RideSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        data = s.validated_data

        driver = data.get('driver')
        if not driver or driver.role != User.ROLE.DRIVER:
            return Response(
                {'detail': 'Selected user is not a driver.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        conflict = Ride.objects.filter(
            driver=driver,
            seat=data['seat'],
            departure_time=data['departure_time'],
            status__in=[Ride.Status.PENDING, Ride.Status.CONFIRMED, Ride.Status.IN_PROGRESS],
        ).exists()
        if conflict:
            return Response(
                {'detail': 'That seat is already booked for this departure.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ride = s.save(
            passenger=request.user,
            status=Ride.Status.PENDING,
            payment_status=Ride.PaymentStatus.UNPAID,
        )
        return Response(RideSerializer(ride).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        parameters=[
            OpenApiParameter(name='from_province', description='Filter by from province ID', required=False, type=OpenApiTypes.INT),
            OpenApiParameter(name='to_province', description='Filter by to province ID', required=False, type=OpenApiTypes.INT),
            OpenApiParameter(name='route', description='Filter by route ID', required=False, type=OpenApiTypes.INT),
            OpenApiParameter(name='car_type', description='Filter by car type (ORDINARY, COMFORT, LUXURY)', required=False, type=OpenApiTypes.STR),
            OpenApiParameter(name='date', description='Filter by date (YYYY-MM-DD)', required=False, type=OpenApiTypes.DATE),
            OpenApiParameter(name='seat', description='Filter by seat (FRONT, BACK)', required=False, type=OpenApiTypes.STR),
        ]
    )
    @action(detail=False, methods=['get'])
    def search(self, request):
        s = RideSearchSerializer(data=request.query_params)
        s.is_valid(raise_exception=True)
        data = s.validated_data

        transports = Transport.objects.all()
        if data.get('from_province'):
            transports = transports.filter(from_province_id=data['from_province'])
        if data.get('to_province'):
            transports = transports.filter(to_province_id=data['to_province'])
        if data.get('route'):
            transports = transports.filter(route_id=data['route'])
        if data.get('car_type'):
            transports = transports.filter(type=data['car_type'])
        if data.get('date') and data.get('seat'):
            busy_ids = Ride.objects.filter(
                seat=data['seat'],
                departure_time__date=data['date'],
                status__in=[Ride.Status.CONFIRMED, Ride.Status.IN_PROGRESS],
            ).values_list('driver_id', flat=True)
            transports = transports.exclude(driver_id__in=busy_ids)

        result = TransportSerializer(transports, many=True).data
        return Response({'count': len(result), 'results': result})

    TRANSITIONS = {
        Ride.Status.PENDING:     [Ride.Status.CONFIRMED,   Ride.Status.CANCELLED],
        Ride.Status.CONFIRMED:   [Ride.Status.IN_PROGRESS, Ride.Status.CANCELLED],
        Ride.Status.IN_PROGRESS: [Ride.Status.COMPLETED],
    }

    @action(detail=True, methods=['patch'], url_path='status')
    def update_status(self, request, pk=None):
        try:
            ride = Ride.objects.get(pk=pk, driver=request.user)
        except Ride.DoesNotExist:
            return Response({'detail': 'Ride not found.'}, status=status.HTTP_404_NOT_FOUND)

        new_status = request.data.get('status')
        allowed    = self.TRANSITIONS.get(ride.status, [])

        if new_status not in allowed:
            return Response(
                {'detail': f"Cannot transition '{ride.status}' → '{new_status}'.",
                 'allowed': allowed},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ride.status = new_status
        ride.save(update_fields=['status', 'updated_at'])

        if new_status == Ride.Status.COMPLETED:
            DriverProfile.objects.filter(driver=ride.driver).update(total_trips=F('total_trips') + 1)
            PassengerProfile.objects.filter(passenger=ride.passenger).update(total_trips=F('total_trips') + 1)

        return Response(RideSerializer(ride).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        try:
            ride = Ride.objects.get(pk=pk, passenger=request.user)
        except Ride.DoesNotExist:
            return Response({'detail': 'Ride not found.'}, status=status.HTTP_404_NOT_FOUND)

        if ride.status not in [Ride.Status.PENDING, Ride.Status.CONFIRMED]:
            return Response(
                {'detail': f"Cannot cancel a ride with status '{ride.status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ride.status = Ride.Status.CANCELLED
        ride.save(update_fields=['status', 'updated_at'])
        return Response(RideSerializer(ride).data)

    @action(detail=True, methods=['patch'])
    def payment(self, request, pk=None):
        try:
            ride = Ride.objects.get(pk=pk, driver=request.user)
        except Ride.DoesNotExist:
            return Response({'detail': 'Ride not found.'}, status=status.HTTP_404_NOT_FOUND)

        if ride.status != Ride.Status.COMPLETED:
            return Response(
                {'detail': 'Payment can only be updated after the ride is completed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        allowed_fields = {'payment_status', 'payment_method'}
        changed = []
        for field, value in request.data.items():
            if field in allowed_fields:
                setattr(ride, field, value)
                changed.append(field)

        if changed:
            ride.save(update_fields=changed + ['updated_at'])

        return Response(RideSerializer(ride).data)


class RatingViewSet(viewsets.GenericViewSet):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated(), IsRideParticipant()]
        return [IsAuthenticated(), IsPassenger()]

    def create(self, request, ride_pk=None):
        try:
            ride = Ride.objects.get(pk=ride_pk)
        except Ride.DoesNotExist:
            return Response({'detail': 'Ride not found.'}, status=status.HTTP_404_NOT_FOUND)

        if ride.passenger != request.user:
            return Response({'detail': 'You can only rate your own rides.'}, status=status.HTTP_403_FORBIDDEN)
        
        if ride.status != Ride.Status.COMPLETED:
            return Response({'detail': 'You can only rate completed rides.'}, status=status.HTTP_400_BAD_REQUEST)
            
        if hasattr(ride, 'rating'):
            return Response({'detail': 'You have already rated this ride.'}, status=status.HTTP_400_BAD_REQUEST)

        s = RatingSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        s.save(ride=ride, passenger=request.user, driver=ride.driver)
        
        driver_profile = ride.driver.driver_profile
        new_avg = Rating.objects.filter(driver=ride.driver).aggregate(Avg('stars'))['stars__avg']
        driver_profile.avg_rating = new_avg
        driver_profile.save(update_fields=['avg_rating'])
        
        return Response(s.data, status=status.HTTP_201_CREATED)

    def list(self, request, ride_pk=None):
        try:
            ride = Ride.objects.get(pk=ride_pk)
        except Ride.DoesNotExist:
            return Response({'detail': 'Ride not found.'}, status=status.HTTP_404_NOT_FOUND)
            
        self.check_object_permissions(request, ride)

        if hasattr(ride, 'rating'):
            return Response(RatingSerializer(ride.rating).data)
        return Response({'detail': 'No rating exists for this ride.'}, status=status.HTTP_404_NOT_FOUND)


class DriverDocumentViewSet(viewsets.GenericViewSet, mixins.ListModelMixin):
    serializer_class = DriverDocumentSerializer

    def get_permissions(self):
        if self.action == 'review':
            return [IsAdminUser()]
        return [IsAuthenticated(), IsDriver()]

    def get_queryset(self):
        if self.request.user.is_staff and self.action == 'review':
            return DriverDocument.objects.all()
        return DriverDocument.objects.filter(driver=self.request.user)

    def create(self, request, *args, **kwargs):
        s = DriverDocumentSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        s.save(driver=request.user, status=DriverDocument.Status.PENDING)
        return Response(s.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch'])
    def review(self, request, pk=None):
        try:
            document = self.get_queryset().get(pk=pk)
        except DriverDocument.DoesNotExist:
            return Response({'detail': 'Document not found.'}, status=status.HTTP_404_NOT_FOUND)

        new_status = request.data.get('status')
        if new_status not in [DriverDocument.Status.APPROVED, DriverDocument.Status.REJECTED]:
            return Response({'detail': 'Invalid status.'}, status=status.HTTP_400_BAD_REQUEST)

        document.status = new_status
        document.admin_note = request.data.get('admin_note', document.admin_note)
        document.reviewed_at = timezone.now()
        document.save(update_fields=['status', 'admin_note', 'reviewed_at'])

        if new_status == DriverDocument.Status.APPROVED and document.doc_type == DriverDocument.DocType.LICENSE_WITH_ID:
            profile = document.driver.driver_profile
            profile.is_verified = True
            profile.save(update_fields=['is_verified'])

        return Response(DriverDocumentSerializer(document).data)