from rest_framework import serializers
from .models import Province, Route, Transport, DriverProfile, PassengerProfile, Ride, Rating, DriverDocument, ChatMessage, Location

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
    driver_rating = serializers.SerializerMethodField()

    class Meta:
        model = Transport
        fields = ['id', 'driver', 'from_province', 'to_province', 'route', 'model', 'year', 'type', 'driver_rating']
        
    def get_driver_rating(self, obj):
        if hasattr(obj.driver, 'driver_profile'):
            return obj.driver.driver_profile.avg_rating
        return None

class DriverProfileSerializer(serializers.ModelSerializer):
    driver = serializers.CharField(source='driver.username', read_only=True)

    class Meta:
        model = DriverProfile
        fields = ['id', 'driver', 'avatar', 'avg_rating', 'total_trips', 'joining_date', 'is_verified']
        read_only_fields = ['avg_rating', 'total_trips', 'joining_date', 'is_verified']

class PassengerProfileSerializer(serializers.ModelSerializer):
    passenger = serializers.CharField(source='passenger.username', read_only=True)

    class Meta:
        model = PassengerProfile
        fields = ['id', 'passenger', 'avatar', 'total_trips', 'joining_date']
        read_only_fields = ['total_trips', 'joining_date']

class RideSerializer(serializers.ModelSerializer):
    passenger = serializers.CharField(source='passenger.username', read_only=True)

    class Meta:
        model = Ride
        fields = [
            'id', 'driver', 'passenger', 'route', 'from_province', 'to_province', 
            'seat', 'departure_time', 'price', 'payment_method', 'payment_status', 
            'status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['payment_status', 'status', 'created_at', 'updated_at']

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
