from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from user_log.models import Account
from product_management.models import Brand, Category, Product
from offer_management.models import Offer, ProductOffer, CategoryOffer
import services.offer_service as offer_service


def create_account(email, username, password='Pass1234!', is_admin=False):
    user = Account.objects.create_user(email=email, username=username, password=password)
    user.is_admin = is_admin
    user.save(update_fields=['is_admin'])
    return user


class OfferServiceTests(TestCase):
    def setUp(self):
        self.brand = Brand.objects.create(name='OfferBrand')
        self.category = Category.objects.create(name='OfferCategory')
        self.product = Product.objects.create(
            title='Offer Product', description='desc', brand=self.brand, category=self.category
        )

    def _make_offer(self, discount, offer_type='product'):
        return Offer.objects.create(
            name=f'Offer {discount}%', description='d', offer_type=offer_type,
            discount_percentage=Decimal(str(discount)),
            start_date=timezone.now() - timedelta(days=1),
            end_date=timezone.now() + timedelta(days=1),
            is_active=True,
        )

    def test_get_best_offer_picks_highest_discount(self):
        low_offer = self._make_offer(10)
        high_offer = self._make_offer(30)
        ProductOffer.objects.create(offer=low_offer, product=self.product)
        ProductOffer.objects.create(offer=high_offer, product=self.product)

        best = offer_service.get_best_offer_for_product(self.product)
        self.assertEqual(best.offer.discount_percentage, Decimal('30'))

    def test_apply_offer_to_price_no_offer_returns_original(self):
        price = offer_service.apply_offer_to_price(Decimal('100.00'), None)
        self.assertEqual(price, Decimal('100.00'))

    def test_apply_offer_to_price_applies_discount(self):
        offer = self._make_offer(20)
        product_offer = ProductOffer.objects.create(offer=offer, product=self.product)
        price = offer_service.apply_offer_to_price(Decimal('200.00'), product_offer)
        self.assertEqual(price, Decimal('160.00'))

    def test_expired_offer_not_selected(self):
        expired = Offer.objects.create(
            name='Expired', description='d', offer_type='product',
            discount_percentage=Decimal('50'),
            start_date=timezone.now() - timedelta(days=10),
            end_date=timezone.now() - timedelta(days=1),
            is_active=True,
        )
        ProductOffer.objects.create(offer=expired, product=self.product)
        best = offer_service.get_best_offer_for_product(self.product)
        self.assertIsNone(best)


class OfferAdminAccessTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = create_account('oadmin@example.com', 'oadmin', is_admin=True)
        self.regular_user = create_account('ouser@example.com', 'ouser', is_admin=False)

    def test_regular_authenticated_user_denied_offer_list(self):
        # Prior to the P0 fix this only required login_required; now it
        # must require admin_required specifically.
        self.client.login(email='ouser@example.com', password='Pass1234!')
        response = self.client.get(reverse('offer_management:offer_list'))
        self.assertEqual(response.status_code, 302)

    def test_admin_user_can_access_offer_list(self):
        self.client.login(email='oadmin@example.com', password='Pass1234!')
        response = self.client.get(reverse('offer_management:offer_list'))
        self.assertEqual(response.status_code, 200)