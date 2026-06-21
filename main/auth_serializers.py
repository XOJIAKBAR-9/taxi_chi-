from datetime import date
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import User, PassengerProfile, DriverProfile, Transport, Ride, Province, Route

class RegisterPassengerSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    phone = serializers.CharField(max_length=15)
    password = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        if User.objects.filter(phone=data['phone']).exists():
            raise serializers.ValidationError({"phone": "Phone number already registered."})
        if User.objects.filter(username=data['username']).exists():
            raise serializers.ValidationError({"username": "Username already taken."})
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        
        user = User(**validated_data)
        user.role = User.ROLE.PASSENGER
        user.set_password(password)
        user.save()
        
        PassengerProfile.objects.create(
            passenger=user,
            joining_date=date.today(),
            total_trips=0
        )
        return user


class RegisterDriverSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    phone = serializers.CharField(max_length=15)
    password = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    
    transport_model = serializers.CharField(max_length=255)
    transport_year = serializers.IntegerField()
    transport_type = serializers.ChoiceField(choices=Transport.TYPE.choices)
    from_province = serializers.CharField(max_length=255)
    to_province = serializers.CharField(max_length=255)

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        if User.objects.filter(phone=data['phone']).exists():
            raise serializers.ValidationError({"phone": "Phone number already registered."})
        if User.objects.filter(username=data['username']).exists():
            raise serializers.ValidationError({"username": "Username already taken."})
        if data['from_province'] == data['to_province']:
            raise serializers.ValidationError({"from_province": "from_province and to_province cannot be the same."})
        return data

    def create(self, validated_data):
        transport_model = validated_data.pop('transport_model')
        transport_year = validated_data.pop('transport_year')
        transport_type = validated_data.pop('transport_type')
        from_province = validated_data.pop('from_province')
        to_province = validated_data.pop('to_province')
        
        validated_data.pop('password2')
        password = validated_data.pop('password')
        
        user = User(**validated_data)
        user.role = User.ROLE.DRIVER
        user.set_password(password)
        user.save()
        
        DriverProfile.objects.create(
            driver=user,
            joining_date=date.today(),
            avg_rating=0.0,
            total_trips=0,
            is_verified=False
        )
        
        Transport.objects.create(
            driver=user,
            model=transport_model,
            year=transport_year,
            type=transport_type,
            from_province=from_province,
            to_province=to_province
        )
        return user


class LoginSerializer(serializers.Serializer):
    phone = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        phone = data.get('phone')
        password = data.get('password')
        
        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            raise ValidationError('Invalid phone or password.')
            
        if not user.check_password(password):
            raise ValidationError('Invalid phone or password.')
            
        return {'user': user}


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    new_password2 = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['new_password'] != data['new_password2']:
            raise serializers.ValidationError({"new_password": "New passwords do not match."})
            
        user = self.context['request'].user
        if not user.check_password(data['old_password']):
            raise serializers.ValidationError({"old_password": "Old password is incorrect."})
            
        return data

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class RideSearchSerializer(serializers.Serializer):
    from_province = serializers.IntegerField(required=False)
    to_province = serializers.IntegerField(required=False)
    route = serializers.IntegerField(required=False)
    car_type = serializers.ChoiceField(choices=Transport.TYPE.choices, required=False)
    date = serializers.DateField(required=False)
    seat = serializers.ChoiceField(choices=Ride.SEAT.choices, required=False)
