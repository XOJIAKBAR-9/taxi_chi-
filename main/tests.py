from datetime import date
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status

from .models import User, Province, Route, Transport, DriverProfile, PassengerProfile, Ride, Rating, LostItemReport

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

    def test_ride_search_returns_driver_id(self):
        res = self.client.get('/api/rides/search/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(res.data['count'], 1)
        first = res.data['results'][0]
        self.assertIn('driver_id', first)
        self.assertIn('verification_badges', first)
        self.assertIn('car_images', first)
        self.assertEqual(first['driver_id'], self.driver_user.id)

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
        ride = self._create_completed_ride()
        self.client.force_authenticate(user=self.passenger_user)
        
        url = f"/api/rides/{ride.id}/rating/"
        res = self.client.post(url, {'stars': 5, 'comment': 'Great driver!'})
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Rating.objects.count(), 1)
        
        self.driver_profile.refresh_from_db()
        self.assertEqual(self.driver_profile.avg_rating, 5.0)
        
        res_dup = self.client.post(url, {'stars': 4})
        self.assertEqual(res_dup.status_code, status.HTTP_400_BAD_REQUEST)
        
        ride2 = Ride.objects.create(
            driver=self.driver_user, passenger=self.passenger_user, route=self.route,
            from_province='tashkent_city', to_province='samarkand', seat=Ride.SEAT.FRONT,
            departure_time=timezone.now(), price=100.0, payment_method=Ride.PaymentMethod.CASH,
            status=Ride.Status.IN_PROGRESS, payment_status=Ride.PaymentStatus.UNPAID
        )
        res_not_completed = self.client.post(f"/api/rides/{ride2.id}/rating/", {'stars': 5})
        self.assertEqual(res_not_completed.status_code, status.HTTP_400_BAD_REQUEST)

    def test_passenger_can_rate_same_driver_on_multiple_rides(self):
        ride1 = self._create_completed_ride()
        ride2 = Ride.objects.create(
            driver=self.driver_user, passenger=self.passenger_user, route=self.route,
            from_province='tashkent_city', to_province='samarkand', seat=Ride.SEAT.FRONT,
            departure_time=timezone.now(), price=120.0, payment_method=Ride.PaymentMethod.CASH,
            status=Ride.Status.COMPLETED, payment_status=Ride.PaymentStatus.PAID
        )
        self.client.force_authenticate(user=self.passenger_user)

        res1 = self.client.post(f"/api/rides/{ride1.id}/rating/", {'stars': 5, 'comment': 'First trip'})
        res2 = self.client.post(f"/api/rides/{ride2.id}/rating/", {'stars': 3, 'comment': 'Second trip'})

        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Rating.objects.filter(passenger=self.passenger_user, driver=self.driver_user).count(), 2)

        self.driver_profile.refresh_from_db()
        self.assertEqual(self.driver_profile.avg_rating, 4.0)

    def _create_completed_ride(self):
        return Ride.objects.create(
            driver=self.driver_user, passenger=self.passenger_user, route=self.route,
            from_province='tashkent_city', to_province='samarkand', seat=Ride.SEAT.BACK,
            departure_time=timezone.now(), price=100.0, payment_method=Ride.PaymentMethod.CASH,
            status=Ride.Status.COMPLETED, payment_status=Ride.PaymentStatus.PAID
        )

    def test_lost_item_report_flow(self):
        ride = self._create_completed_ride()
        url = f"/api/rides/{ride.id}/lost-item/"

        self.client.force_authenticate(user=self.passenger_user)
        res = self.client.post(url, {
            'item_description': 'Black backpack',
            'share_contact': True,
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(LostItemReport.objects.count(), 1)
        self.assertIn('Black backpack', res.data['notification_message'])
        self.assertEqual(res.data['status'], LostItemReport.Status.OPEN)

        res_dup = self.client.post(url, {'item_description': 'Phone'})
        self.assertEqual(res_dup.status_code, status.HTTP_400_BAD_REQUEST)

        self.client.force_authenticate(user=self.driver_user)
        pending = self.client.get('/api/drivers/lost-item-reports/')
        self.assertEqual(pending.status_code, status.HTTP_200_OK)
        self.assertEqual(len(pending.data), 1)
        self.assertEqual(pending.data[0]['passenger_contact'], self.passenger_user.phone)

        res_yes = self.client.patch(f"{url}respond/", {'driver_response': 'yes'})
        self.assertEqual(res_yes.status_code, status.HTTP_200_OK)
        self.assertEqual(res_yes.data['status'], LostItemReport.Status.FOUND)
        self.assertEqual(res_yes.data['driver_response'], LostItemReport.DriverResponse.YES)

        pending_after = self.client.get('/api/drivers/lost-item-reports/')
        self.assertEqual(len(pending_after.data), 0)

    def test_driver_cannot_report_lost_item(self):
        ride = self._create_completed_ride()
        url = f"/api/rides/{ride.id}/lost-item/"

        self.client.force_authenticate(user=self.driver_user)
        res = self.client.post(url, {
            'item_description': 'Wallet',
            'share_contact': False,
        })
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_passenger_lost_item_notification_messages(self):
        ride = self._create_completed_ride()
        url = f"/api/rides/{ride.id}/lost-item/"

        self.client.force_authenticate(user=self.passenger_user)
        res = self.client.post(url, {
            'item_description': 'Black backpack',
            'share_contact': False,
        })
        self.assertIn('Black backpack', res.data['passenger_notification_message'])

        self.client.force_authenticate(user=self.driver_user)
        res_yes = self.client.patch(f"{url}respond/", {'driver_response': 'yes'})
        self.assertIn('found your Black backpack', res_yes.data['passenger_notification_message'])

        ride2 = self._create_completed_ride()
        url2 = f"/api/rides/{ride2.id}/lost-item/"
        self.client.force_authenticate(user=self.passenger_user)
        self.client.post(url2, {'item_description': 'Phone', 'share_contact': False})

        self.client.force_authenticate(user=self.driver_user)
        res_no = self.client.patch(f"{url2}respond/", {'driver_response': 'no'})
        self.assertIn('could not find your Phone', res_no.data['passenger_notification_message'])

        passenger_reports = self.client.get('/api/passengers/lost-item-reports/')
        self.client.force_authenticate(user=self.passenger_user)
        passenger_reports = self.client.get('/api/passengers/lost-item-reports/')
        self.assertEqual(passenger_reports.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(passenger_reports.data), 2)

    def test_lost_item_report_requires_completed_ride(self):
        ride = Ride.objects.create(
            driver=self.driver_user, passenger=self.passenger_user, route=self.route,
            from_province='tashkent_city', to_province='samarkand', seat=Ride.SEAT.FRONT,
            departure_time=timezone.now(), price=100.0, payment_method=Ride.PaymentMethod.CASH,
            status=Ride.Status.IN_PROGRESS, payment_status=Ride.PaymentStatus.UNPAID
        )
        self.client.force_authenticate(user=self.passenger_user)
        res = self.client.post(f"/api/rides/{ride.id}/lost-item/", {
            'item_description': 'Wallet',
            'share_contact': False,
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_ride_end_by_passenger_and_driver(self):
        ride = Ride.objects.create(
            driver=self.driver_user, passenger=self.passenger_user, route=self.route,
            from_province='tashkent_city', to_province='samarkand', seat=Ride.SEAT.BACK,
            departure_time=timezone.now(), price=100.0, payment_method=Ride.PaymentMethod.CASH,
            status=Ride.Status.PENDING, payment_status=Ride.PaymentStatus.UNPAID
        )

        self.client.force_authenticate(user=self.passenger_user)
        res = self.client.post(f"{self.ride_url}{ride.id}/end/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['status'], Ride.Status.COMPLETED)

        ride.refresh_from_db()
        self.assertEqual(ride.status, Ride.Status.COMPLETED)
        self.passenger_profile.refresh_from_db()
        self.driver_profile.refresh_from_db()
        self.assertEqual(self.passenger_profile.total_trips, 1)
        self.assertEqual(self.driver_profile.total_trips, 1)

        res_again = self.client.post(f"{self.ride_url}{ride.id}/end/")
        self.assertEqual(res_again.status_code, status.HTTP_400_BAD_REQUEST)

        ride2 = Ride.objects.create(
            driver=self.driver_user, passenger=self.passenger_user, route=self.route,
            from_province='tashkent_city', to_province='samarkand', seat=Ride.SEAT.FRONT,
            departure_time=timezone.now(), price=80.0, payment_method=Ride.PaymentMethod.CASH,
            status=Ride.Status.IN_PROGRESS, payment_status=Ride.PaymentStatus.UNPAID
        )
        self.client.force_authenticate(user=self.driver_user)
        res_driver = self.client.post(f"{self.ride_url}{ride2.id}/end/")
        self.assertEqual(res_driver.status_code, status.HTTP_200_OK)
        self.assertEqual(res_driver.data['status'], Ride.Status.COMPLETED)
