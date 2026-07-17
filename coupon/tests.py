from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from user_log.models import Account
from coupon.models import Coupon
import services.coupon_service as coupon_service


def create_account(email, username, password='Pass1234!', is_admin=False):
    user = Account.objects.create_user(email=email, username=username, password=password)
    user.is_admin = is_admin
    user.save(update_fields=['is_admin'])
    return user


class CouponServiceTests(TestCase):
    def setUp(self):
        self.valid_coupon = Coupon.objects.create(
            code='SAVE10', discount_type='percentage', discount_value=Decimal('10'),
            expiration_date=timezone.now() + timedelta(days=5), active=True,
        )
        self.expired_coupon = Coupon.objects.create(
            code='OLD10', discount_type='percentage', discount_value=Decimal('10'),
            expiration_date=timezone.now() - timedelta(days=1), active=True,
        )

    def test_get_active_coupon_success(self):
        coupon = coupon_service.get_active_coupon('SAVE10')
        self.assertEqual(coupon.code, 'SAVE10')

    def test_get_active_coupon_expired_raises(self):
        with self.assertRaises(coupon_service.CouponError):
            coupon_service.get_active_coupon('OLD10')

    def test_get_active_coupon_nonexistent_raises(self):
        with self.assertRaises(coupon_service.CouponError):
            coupon_service.get_active_coupon('NOPE')

    def test_calculate_discount_percentage(self):
        discount = coupon_service.calculate_discount(self.valid_coupon, Decimal('1000.00'))
        self.assertEqual(discount, Decimal('100.00'))

    def test_calculate_discount_fixed_amount_capped_at_cart_total(self):
        fixed_coupon = Coupon.objects.create(
            code='FLAT500', discount_type='amount', discount_value=Decimal('500'),
            expiration_date=timezone.now() + timedelta(days=5), active=True,
        )
        discount = coupon_service.calculate_discount(fixed_coupon, Decimal('300.00'))
        self.assertEqual(discount, Decimal('300.00'))  # capped, not 500

    def test_validate_coupon_for_cart_below_minimum_raises(self):
        self.valid_coupon.min_purchase_amount = Decimal('2000.00')
        self.valid_coupon.save()
        with self.assertRaises(coupon_service.CouponError):
            coupon_service.validate_coupon_for_cart('SAVE10', Decimal('500.00'))


class CouponAdminAccessTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = create_account('cadmin@example.com', 'cadmin', is_admin=True)
        self.regular_user = create_account('cuser@example.com', 'cuser', is_admin=False)

    def test_regular_user_cannot_access_coupon_list(self):
        self.client.login(email='cuser@example.com', password='Pass1234!')
        response = self.client.get(reverse('coupon:coupon_list'))
        self.assertEqual(response.status_code, 302)

    def test_admin_can_access_coupon_list(self):
        self.client.login(email='cadmin@example.com', password='Pass1234!')
        response = self.client.get(reverse('coupon:coupon_list'))
        self.assertEqual(response.status_code, 200)

    def test_anonymous_user_can_still_apply_coupon_route_requires_login(self):
        response = self.client.post(reverse('coupon:apply_coupon'), {'code': 'SAVE10'})
        self.assertEqual(response.status_code, 302)  # redirected to login, not admin_required