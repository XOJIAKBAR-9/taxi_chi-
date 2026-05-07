from django.contrib import admin
from .models import *

admin.site.register(User)
admin.site.register(Province)
admin.site.register(Route)
admin.site.register(Transport)
admin.site.register(DriverProfile)
admin.site.register(PassengerProfile)
admin.site.register(Ride)
