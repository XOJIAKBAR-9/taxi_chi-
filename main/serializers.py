from rest_framework import serializers
from .models import Province, Route, Transport, DriverProfile, PassengerProfile, Ride, Rating, DriverDocument, ChatMessage, Location, LostItemReport, ProvinceChoices
from .notifications import (
    build_driver_lost_item_notification,
    build_passenger_report_submitted_message,
    build_passenger_found_message,
    build_passenger_not_found_message,
)

class ProvinceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Province
        fields = ['id', 'name']

class RouteSerializer(serializers.ModelSerializer):
    province = ProvinceSerializer(read_only=True)
    province_id = serializers.PrimaryKeyRelatedField(
        queryset=Province.objects.all(), source='province', write_only=True
    )

    class Meta:
        model = Route
        fields = ['id', 'name', 'province', 'province_id']

class TransportSerializer(serializers.ModelSerializer):
    driver = serializers.CharField(source='driver.username', read_only=True)
    driver_id = serializers.IntegerField(source='driver.id', read_only=True)
    driver_rating = serializers.SerializerMethodField()
    verification_badges = serializers.SerializerMethodField()
    car_images = serializers.SerializerMethodField()

    class Meta:
        model = Transport
        fields = [
            'id', 'driver_id', 'driver', 'from_province', 'to_province', 'route',
            'model', 'year', 'type', 'driver_rating', 'verification_badges', 'car_images'
        ]
        
    def get_driver_rating(self, obj):
        if hasattr(obj.driver, 'driver_profile'):
            return obj.driver.driver_profile.avg_rating
        return None

    def get_verification_badges(self, obj):
        return {
            'license_with_id_verified': DriverDocument.objects.filter(
                driver=obj.driver,
                doc_type=DriverDocument.DocType.LICENSE_WITH_ID,
                status=DriverDocument.Status.APPROVED,
            ).exists(),
            'vehicle_registration_verified': DriverDocument.objects.filter(
                driver=obj.driver,
                doc_type=DriverDocument.DocType.VEHICLE_REGISTRATION,
                status=DriverDocument.Status.APPROVED,
            ).exists(),
        }

    def get_car_images(self, obj):
        request = self.context.get('request')
        docs = DriverDocument.objects.filter(
            driver=obj.driver,
            doc_type=DriverDocument.DocType.CAR_PHOTO,
            status=DriverDocument.Status.APPROVED,
        ).order_by('-uploaded_at')[:4]

        images = []
        for d in docs:
            if not d.file:
                continue
            url = d.file.url
            if request:
                url = request.build_absolute_uri(url)
            images.append({
                'id': d.id,
                'url': url,
            })
        return images

class DriverProfileSerializer(serializers.ModelSerializer):
    driver = serializers.CharField(source='driver.username', read_only=True)
    transport = serializers.SerializerMethodField()

    class Meta:
        model = DriverProfile
        fields = ['id', 'driver', 'avatar', 'avg_rating', 'total_trips', 'joining_date', 'is_verified', 'is_online', 'transport']
        read_only_fields = ['avg_rating', 'total_trips', 'joining_date', 'is_verified']

    def get_transport(self, obj):
        try:
            t = obj.driver.transport_info
            return {'model': t.model, 'year': t.year, 'type': t.type,
                    'from_province': t.from_province, 'to_province': t.to_province}
        except Exception:
            return None

class PassengerProfileSerializer(serializers.ModelSerializer):
    passenger = serializers.CharField(source='passenger.username', read_only=True)

    class Meta:
        model = PassengerProfile
        fields = ['id', 'passenger', 'avatar', 'total_trips', 'joining_date']
        read_only_fields = ['total_trips', 'joining_date']

class RideSerializer(serializers.ModelSerializer):
    passenger      = serializers.CharField(source='passenger.username', read_only=True)
    driver_name    = serializers.CharField(source='driver.username', read_only=True)
    from_province  = serializers.ChoiceField(choices=ProvinceChoices.choices)
    to_province    = serializers.ChoiceField(choices=ProvinceChoices.choices)
    lost_item_report_status = serializers.SerializerMethodField()

    class Meta:
        model = Ride
        fields = [
            'id', 'driver', 'driver_name', 'passenger', 'route', 'from_province', 'to_province', 
            'seat', 'departure_time', 'price', 'payment_method', 'payment_status', 
            'status', 'lost_item_report_status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['payment_status', 'status', 'created_at', 'updated_at', 'lost_item_report_status', 'driver_name']

    def get_lost_item_report_status(self, obj):
        report = getattr(obj, 'lost_item_report', None)
        return report.status if report else None

    def validate(self, data):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            from .models import User
            if request.user.role == User.ROLE.DRIVER:
                raise serializers.ValidationError(
                    'Active drivers are not permitted to book rides.'
                )
        return data

class RatingSerializer(serializers.ModelSerializer):
    passenger = serializers.CharField(source='passenger.username', read_only=True)
    driver = serializers.CharField(source='driver.username', read_only=True)

    class Meta:
        model = Rating
        fields = ['id', 'ride', 'passenger', 'driver', 'stars', 'comment', 'created_at']
        read_only_fields = ['created_at']

class DriverDocumentSerializer(serializers.ModelSerializer):
    driver = serializers.CharField(source='driver.username', read_only=True)

    class Meta:
        model = DriverDocument
        fields = ['id', 'driver', 'doc_type', 'file', 'status', 'admin_note', 'uploaded_at']
        read_only_fields = ['status', 'admin_note', 'uploaded_at']


class ChatMessageSerializer(serializers.ModelSerializer):
    sender = serializers.CharField(source='sender.username', read_only=True)
    sender_id = serializers.IntegerField(source='sender.id', read_only=True)

    class Meta:
        model = ChatMessage
        fields = ['id', 'ride', 'sender', 'sender_id', 'message', 'timestamp', 'is_read']
        read_only_fields = ['timestamp', 'sender']


class LocationSerializer(serializers.ModelSerializer):
    driver = serializers.CharField(source='driver.username', read_only=True)
    driver_id = serializers.IntegerField(source='driver.id', read_only=True)

    class Meta:
        model = Location
        fields = ['id', 'ride', 'driver', 'driver_id', 'latitude', 'longitude', 'timestamp']
        read_only_fields = ['timestamp', 'driver']


class LostItemReportSerializer(serializers.ModelSerializer):
    passenger = serializers.CharField(source='passenger.username', read_only=True)
    driver = serializers.CharField(source='driver.username', read_only=True)
    passenger_contact = serializers.SerializerMethodField()
    vehicle_model = serializers.SerializerMethodField()
    notification_message = serializers.SerializerMethodField()
    passenger_notification_message = serializers.SerializerMethodField()

    class Meta:
        model = LostItemReport
        fields = [
            'id', 'ride', 'passenger', 'driver', 'item_description', 'share_contact',
            'status', 'driver_response', 'passenger_contact', 'vehicle_model',
            'notification_message', 'passenger_notification_message',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'ride', 'passenger', 'driver',
            'status', 'driver_response', 'passenger_contact', 'vehicle_model',
            'notification_message', 'passenger_notification_message',
            'created_at', 'updated_at',
        ]

    def get_vehicle_model(self, obj):
        try:
            return obj.driver.transport_info.model
        except Exception:
            return 'vehicle'

    def get_notification_message(self, obj):
        return build_driver_lost_item_notification(obj.item_description, self.get_vehicle_model(obj))

    def get_passenger_notification_message(self, obj):
        if obj.driver_response == LostItemReport.DriverResponse.PENDING:
            return build_passenger_report_submitted_message(obj.item_description)
        if obj.driver_response == LostItemReport.DriverResponse.YES:
            return build_passenger_found_message(obj.item_description, obj.driver.username)
        if obj.driver_response == LostItemReport.DriverResponse.NO:
            return build_passenger_not_found_message(obj.item_description, obj.driver.username)
        return None

    def get_passenger_contact(self, obj):
        request = self.context.get('request')
        if not obj.share_contact:
            return None
        if not request or not request.user.is_authenticated:
            return None
        if request.user != obj.driver and request.user != obj.passenger and not request.user.is_staff:
            return None
        return obj.passenger.phone
