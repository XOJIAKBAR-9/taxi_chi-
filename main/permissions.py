from rest_framework.permissions import BasePermission
from .models import User

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
