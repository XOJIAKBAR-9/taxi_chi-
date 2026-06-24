from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import AbstractUser


class ProvinceChoices(models.TextChoices):
    ANDIJAN        = 'andijan',        'Andijan'
    BUKHARA        = 'bukhara',        'Bukhara'
    FERGANA        = 'fergana',        'Fergana'
    JIZZAKH        = 'jizzakh',        'Jizzakh'
    KARAKALPAKSTAN = 'karakalpakstan', 'Karakalpakstan'
    KASHKADARYA    = 'kashkadarya',    'Kashkadarya'
    KHOREZM        = 'khorezm',        'Khorezm'
    NAMANGAN       = 'namangan',       'Namangan'
    NAVOIY         = 'navoiy',         'Navoiy'
    SAMARKAND      = 'samarkand',      'Samarkand'
    SIRDARYO       = 'sirdaryo',       'Sirdaryo'
    SURKHANDARYA   = 'surkhandarya',   'Surkhandarya'
    TASHKENT_CITY  = 'tashkent_city',  'Tashkent City'
    TASHKENT_REGION= 'tashkent_region','Tashkent Region'


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

    driver = models.OneToOneField(User, on_delete=models.CASCADE, related_name="transport_info")
    from_province = models.CharField(max_length=50, choices=ProvinceChoices.choices)
    to_province   = models.CharField(max_length=50, choices=ProvinceChoices.choices)
    route = models.ForeignKey(Route, on_delete=models.CASCADE, null=True, blank=True)
    model = models.CharField(max_length=255)
    year = models.IntegerField()
    type = models.CharField(max_length=20, choices=TYPE.choices)

    def __str__(self):
        return f"{self.driver.username} - {self.model}"


class DriverProfile(models.Model):
    driver = models.OneToOneField(User, on_delete=models.CASCADE, related_name="driver_profile")
    avatar = models.ImageField(upload_to='drivers/avatars/', blank=True)
    avg_rating = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(5.0)])
    total_trips = models.IntegerField(default=0)
    joining_date = models.DateField()
    is_verified = models.BooleanField(default=False)
    is_online = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.driver.username} - {self.avg_rating}"


class PassengerProfile(models.Model):
    passenger = models.OneToOneField(User, on_delete=models.CASCADE, related_name="passenger_profile")
    avatar = models.ImageField(upload_to='passengers/avatars/', blank=True)
    total_trips = models.IntegerField(default=0)
    joining_date = models.DateField()

    def __str__(self):
        return f"{self.passenger.username}"


class DriverDocument(models.Model):
    class DocType(models.TextChoices):
        LICENSE_WITH_ID       = 'LICENSE_WITH_ID',       'Driver License with Self ID Card'
        VEHICLE_REGISTRATION  = 'VEHICLE_REGISTRATION',  'Vehicle Registration (Tech Passport)'
        CAR_PHOTO             = 'CAR_PHOTO',             'Car Interior / Exterior Photo'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending Review'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    driver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    doc_type = models.CharField(max_length=25, choices=DocType.choices, default=DocType.LICENSE_WITH_ID)
    file = models.FileField(upload_to='driver_docs/')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    admin_note = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.driver.username} - {self.doc_type} ({self.status})"


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

    driver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="rides_given")
    passenger = models.ForeignKey(User, on_delete=models.CASCADE, related_name="rides_taken")

    route = models.ForeignKey(Route, on_delete=models.CASCADE, null=True, blank=True)
    from_province = models.CharField(max_length=50, choices=ProvinceChoices.choices, default='tashkent_city')
    to_province   = models.CharField(max_length=50, choices=ProvinceChoices.choices, default='tashkent_city')

    seat = models.CharField(max_length=20, choices=SEAT.choices)
    departure_time = models.DateTimeField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.passenger.username} - from {self.from_province} to {self.to_province}"


class Rating(models.Model):
    ride = models.OneToOneField(Ride, on_delete=models.CASCADE, related_name='rating')
    passenger = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ratings_given')
    driver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ratings_received')
    stars = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.passenger} → {self.driver}: {self.stars}★"


class ChatMessage(models.Model):
    ride = models.ForeignKey(Ride, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.sender.username} - {self.ride.id}: {self.message[:50]}"


class Location(models.Model):
    ride = models.ForeignKey(Ride, on_delete=models.CASCADE, related_name='locations')
    driver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='location_updates')
    latitude = models.FloatField()
    longitude = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.driver.username} - ({self.latitude}, {self.longitude}) at {self.timestamp}"