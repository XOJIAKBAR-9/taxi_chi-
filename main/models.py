from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    class ROLE(models.TextChoices):
        DRIVER = 'DRIVER', 'Driver'
        PASSENGER = 'PASSENGER', 'Passenger'

    phone = models.CharField(max_length=15, unique=True)
    role = models.CharField(max_length=20, choices=ROLE.choices, default=ROLE.PASSENGER)

    def __str__(self):
        return self.username


class Province(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Route(models.Model):
    province = models.ForeignKey(Province, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Transport(models.Model):
    class TYPE(models.TextChoices):
        ORDINARY = "ORDINARY", "Ordinary"
        COMFORT = "COMFORT", "Comfort"
        LUXURY = "LUXURY", "Luxury"

    # Changed related_name to be specific to Transport
    driver = models.OneToOneField(User, on_delete=models.CASCADE, related_name="transport_info")
    from_province = models.ForeignKey(Province, on_delete=models.CASCADE, related_name="transports_from")
    to_province = models.ForeignKey(Province, on_delete=models.CASCADE, related_name="transports_to")
    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    model = models.CharField(max_length=255)
    year = models.IntegerField()
    type = models.CharField(max_length=20, choices=TYPE.choices)

    def __str__(self):
        return f"{self.driver.username} - {self.model}"


class DriverProfile(models.Model):
    # Changed related_name to be specific to the Profile
    driver = models.OneToOneField(User, on_delete=models.CASCADE, related_name="driver_profile")
    avatar = models.ImageField(upload_to='drivers/avatars/', blank=True)
    avg_rating = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(5.0)])
    total_trips = models.IntegerField(default=0)
    joining_date = models.DateField()

    def __str__(self):
        return f"{self.driver.username} - {self.avg_rating}"


class PassengerProfile(models.Model):
    # Changed related_name to lowercase/standard convention
    passenger = models.OneToOneField(User, on_delete=models.CASCADE, related_name="passenger_profile")
    avatar = models.ImageField(upload_to='passengers/avatars/', blank=True)
    total_trips = models.IntegerField(default=0)
    joining_date = models.DateField()

    def __str__(self):
        return f"{self.passenger.username}"


class Ride(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    class SEAT(models.TextChoices):
        FRONT = 'FRONT', 'Front'
        BACK = 'BACK', 'Back'

    class PaymentMethod(models.TextChoices):
        CASH = "cash", "Cash"
        CARD = "card", "Card"

    class PaymentStatus(models.TextChoices):
        UNPAID = "unpaid", "Unpaid"
        PAID = "paid", "Paid"

    # Unique related_names for Ride history
    driver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="rides_given")
    passenger = models.ForeignKey(User, on_delete=models.CASCADE, related_name="rides_taken")

    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    # Unique related_names for Province lookups
    from_province = models.ForeignKey(Province, on_delete=models.CASCADE, related_name="rides_starting_at")
    to_province = models.ForeignKey(Province, on_delete=models.CASCADE, related_name="rides_ending_at")

    seat = models.CharField(max_length=20, choices=SEAT.choices)
    departure_time = models.DateTimeField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.passenger.username} - from {self.from_province} to {self.to_province}"