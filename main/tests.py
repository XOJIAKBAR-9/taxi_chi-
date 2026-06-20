from datetime import date
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status

from .models import User, Province, Route, Transport, DriverProfile, PassengerProfile, Ride, Rating

class TaxiChiTests(APITestCase):
    def setUp(self):
        self.province1 = Province.objects.create(name='Tashkent')
        self.province2 = Province.objects.create(name='Samarkand')
        self.route = Route.objects.create(province=self.province1, name='Tashkent-Samarkand Route')
        
        self.passenger_user = User.objects.create_user(
            username='passenger1', phone='+998901234567', password='pass123', role=User.ROLE.PASSENGER
        )
        self.passenger_profile = PassengerProfile.objects.create(
            passenger=self.passenger_user, joining_date=date.today()
        )
        
        self.driver_user = User.objects.create_user(
            username='driver1', phone='+998907654321', password='pass123', role=User.ROLE.DRIVER
        )
        self.driver_profile = DriverProfile.objects.create(
            driver=self.driver_user, joining_date=date.today(), avg_rating=0.0
        )
        self.transport = Transport.objects.create(
            driver=self.driver_user, model='Cobalt', year=2020, type=Transport.TYPE.COMFORT,
            from_province=self.province1, to_province=self.province2, route=self.route
        )
        self.ride_url = '/api/rides/'

    def test_auth_register_passenger(self):
        url = '/api/auth/register/passenger/'
        data = {
            'username': 'newpass',
            'phone': '+998991112233',
            'password': 'Password123',
            'password2': 'Password123'
        }
        res = self.client.post(url, data)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn('access', res.data)
        self.assertTrue(User.objects.filter(username='newpass').exists())

    def test_auth_register_duplicate_phone(self):
        url = '/api/auth/register/passenger/'
        data = {
            'username': 'anotherpass',
            'phone': '+998901234567',
            'password': 'Password123',
            'password2': 'Password123'
        }
        res = self.client.post(url, data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('phone', res.data)

    def test_auth_register_driver(self):
        url = '/api/auth/register/driver/'
        data = {
            'username': 'newdriver',
            'phone': '+998994445566',
            'password': 'Password123',
            'password2': 'Password123',
            'transport_model': 'Lacetti',
            'transport_year': 2018,
            'transport_type': Transport.TYPE.ORDINARY,
            'from_province': self.province1.id,
            'to_province': self.province2.id,
            'route': self.route.id
        }
        res = self.client.post(url, data)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username='newdriver')
        self.assertEqual(user.role, User.ROLE.DRIVER)
        self.assertTrue(hasattr(user, 'transport_info'))
        self.assertEqual(user.transport_info.model, 'Lacetti')

    def test_auth_login_success_and_wrong_password(self):
        url = '/api/auth/login/'
        res_success = self.client.post(url, {'phone': '+998901234567', 'password': 'pass123'})
        self.assertEqual(res_success.status_code, status.HTTP_200_OK)
        self.assertIn('access', res_success.data)
        
        res_fail = self.client.post(url, {'phone': '+998901234567', 'password': 'wrong'})
        self.assertEqual(res_fail.status_code, status.HTTP_400_BAD_REQUEST)

    def test_auth_change_password(self):
        url = '/api/auth/change-password/'
        self.client.force_authenticate(user=self.passenger_user)
        data = {
            'old_password': 'pass123',
            'new_password': 'NewPassword1!',
            'new_password2': 'NewPassword1!'
        }
        res = self.client.post(url, data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.passenger_user.refresh_from_db()
        self.assertTrue(self.passenger_user.check_password('NewPassword1!'))

    def test_permissions_access_control(self):
        self.client.force_authenticate(user=self.passenger_user)
        res = self.client.get('/api/drivers/me/')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        
        self.client.force_authenticate(user=None)
        res = self.client.get('/api/rides/')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_ride_create_and_duplicate_block(self):
        self.client.force_authenticate(user=self.passenger_user)
        data = {
            'driver': self.driver_user.id,
            'route': self.route.id,
            'from_province': self.province1.id,
            'to_province': self.province2.id,
            'seat': Ride.SEAT.FRONT,
            'departure_time': timezone.now() + timezone.timedelta(days=1),
            'price': '50000.00',
            'payment_method': Ride.PaymentMethod.CASH
        }
        res = self.client.post(self.ride_url, data)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        
        res_dup = self.client.post(self.ride_url, data)
        self.assertEqual(res_dup.status_code, status.HTTP_400_BAD_REQUEST)

    def test_ride_status_transitions(self):
        ride = Ride.objects.create(
            driver=self.driver_user, passenger=self.passenger_user, route=self.route,
            from_province=self.province1, to_province=self.province2,
            seat=Ride.SEAT.BACK, departure_time=timezone.now(),
            price=100.0, payment_method=Ride.PaymentMethod.CASH,
            status=Ride.Status.PENDING, payment_status=Ride.PaymentStatus.UNPAID
        )
        self.client.force_authenticate(user=self.driver_user)
        
        res = self.client.patch(f"{self.ride_url}{ride.id}/status/", {'status': Ride.Status.CONFIRMED})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['status'], Ride.Status.CONFIRMED)
        
        res_invalid = self.client.patch(f"{self.ride_url}{ride.id}/status/", {'status': Ride.Status.PENDING})
        self.assertEqual(res_invalid.status_code, status.HTTP_400_BAD_REQUEST)

    def test_ride_cancel(self):
        ride = Ride.objects.create(
            driver=self.driver_user, passenger=self.passenger_user, route=self.route,
            from_province=self.province1, to_province=self.province2, seat=Ride.SEAT.BACK,
            departure_time=timezone.now(), price=100.0, payment_method=Ride.PaymentMethod.CASH,
            status=Ride.Status.PENDING, payment_status=Ride.PaymentStatus.UNPAID
        )
        self.client.force_authenticate(user=self.passenger_user)
        res = self.client.post(f"{self.ride_url}{ride.id}/cancel/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['status'], Ride.Status.CANCELLED)

    def test_rating_creation_and_blocking(self):
        ride = Ride.objects.create(
            driver=self.driver_user, passenger=self.passenger_user, route=self.route,
            from_province=self.province1, to_province=self.province2, seat=Ride.SEAT.BACK,
            departure_time=timezone.now(), price=100.0, payment_method=Ride.PaymentMethod.CASH,
            status=Ride.Status.COMPLETED, payment_status=Ride.PaymentStatus.PAID
        )
        self.client.force_authenticate(user=self.passenger_user)
        
        url = f"/api/rides/{ride.id}/rating/"
        res = self.client.post(url, {'stars': 5, 'comment': 'Great driver!'})
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Rating.objects.count(), 1)
        
        self.driver_profile.refresh_from_db()
        self.assertEqual(self.driver_profile.avg_rating, 5.0)
        
        res_dup = self.client.post(url, {'stars': 4})
        self.assertEqual(res_dup.status_code, status.HTTP_400_BAD_REQUEST)
        
        ride.status = Ride.Status.IN_PROGRESS
        ride.save()
        ride2 = Ride.objects.create(
            driver=self.driver_user, passenger=self.passenger_user, route=self.route,
            from_province=self.province1, to_province=self.province2, seat=Ride.SEAT.FRONT,
            departure_time=timezone.now(), price=100.0, payment_method=Ride.PaymentMethod.CASH,
            status=Ride.Status.IN_PROGRESS, payment_status=Ride.PaymentStatus.UNPAID
        )
        res_not_completed = self.client.post(f"/api/rides/{ride2.id}/rating/", {'stars': 5})
        self.assertEqual(res_not_completed.status_code, status.HTTP_400_BAD_REQUEST)
