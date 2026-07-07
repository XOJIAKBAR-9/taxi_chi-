from django.contrib import admin
from django.utils import timezone
from .models import User, Province, Route, Transport, DriverProfile, PassengerProfile, Ride, Rating, DriverDocument, LostItemReport

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'phone', 'role', 'is_active')
    list_filter = ('role',)
    search_fields = ('username', 'phone')

@admin.register(DriverProfile)
class DriverProfileAdmin(admin.ModelAdmin):
    list_display = ('driver', 'avg_rating', 'total_trips', 'is_verified')
    list_filter = ('is_verified',)
    readonly_fields = ('avg_rating', 'total_trips')

@admin.register(Ride)
class RideAdmin(admin.ModelAdmin):
    list_display = ('passenger', 'driver', 'from_province', 'to_province', 'status', 'departure_time', 'price')
    list_filter = ('status', 'payment_status')
    search_fields = ('passenger__username', 'driver__username')

@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('ride', 'passenger', 'driver', 'stars', 'created_at')
    list_filter = ('stars',)

@admin.register(DriverDocument)
class DriverDocumentAdmin(admin.ModelAdmin):
    list_display = ('driver', 'doc_type', 'status', 'uploaded_at', 'reviewed_at')
    list_filter = ('status', 'doc_type')
    readonly_fields = ('reviewed_at',)
    actions = ['approve_documents']

    @admin.action(description='Approve selected pending documents')
    def approve_documents(self, request, queryset):
        for doc in queryset.filter(status=DriverDocument.Status.PENDING):
            doc.status = DriverDocument.Status.APPROVED
            doc.reviewed_at = timezone.now()
            doc.save()
            if doc.doc_type == DriverDocument.DocType.LICENSE_WITH_ID:
                profile = doc.driver.driver_profile
                profile.is_verified = True
                profile.save()


@admin.register(LostItemReport)
class LostItemReportAdmin(admin.ModelAdmin):
    list_display = ('ride', 'passenger', 'driver', 'item_description', 'status', 'driver_response', 'created_at')
    list_filter = ('status', 'driver_response', 'share_contact')
    search_fields = ('item_description', 'passenger__username', 'driver__username')
    readonly_fields = ('created_at', 'updated_at')

admin.site.register(Province)
admin.site.register(Route)
admin.site.register(Transport)
admin.site.register(PassengerProfile)
