from .models import *
from rest_framework.serializers import ModelSerializer

class ProvinceSerializer(ModelSerializer):
    class Meta:
        model = Province
        fields = "__all__"

class RouteSerializer(ModelSerializer):
    class Meta:
        model = Route
        fields = "__all__"

class TransportSerializer(ModelSerializer):
    class Meta:
        model = Transport
        fields = "__all__"

class DriverProfileSerializer(ModelSerializer):
    class Meta:
        model = DriverProfile
        fields = "__all__"

class PassengerProfileSerializer(ModelSerializer):
    class Meta:
        model = PassengerProfile
        fields = "__all__"

class RideSerializer(ModelSerializer):
    class Meta:
        model = Ride
        fields = "__all__"