from rest_framework.permissions import BasePermission
from .models import User, Ride

class IsDriver(BasePermission):
    """Allow access only to authenticated users with role=DRIVER."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == User.ROLE.DRIVER)

class IsPassenger(BasePermission):
    """Allow access only to authenticated users with role=PASSENGER."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == User.ROLE.PASSENGER)

class IsRideParticipant(BasePermission):
    """Allow access only to the driver or passenger of the specific ride object."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)
        
    def has_object_permission(self, request, view, obj):
        return obj.driver == request.user or obj.passenger == request.user


class IsRideParticipantByURL(BasePermission):
    """Allow access only to ride participants based on ride_pk in URL kwargs."""
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        
        ride_pk = view.kwargs.get('ride_pk')
        if not ride_pk:
            return True  # Allow if ride_pk is not in URL (shouldn't happen but fallback)
        
        try:
            ride = Ride.objects.get(pk=ride_pk)
            return ride.driver == request.user or ride.passenger == request.user
        except Ride.DoesNotExist:
            return False


class IsVerifiedDriver(BasePermission):
    """Allow access only to drivers whose DriverProfile.is_verified is True."""
    def has_permission(self, request, view):
        return bool(
            request.user 
            and request.user.is_authenticated 
            and request.user.role == User.ROLE.DRIVER
            and hasattr(request.user, 'driver_profile')
            and request.user.driver_profile.is_verified
        )
