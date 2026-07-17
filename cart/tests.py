from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse

from user_log.models import Account
from product_management.models import Brand, Category, Color, Product, ProductVariant
from cart.forms import AddToCartForm


def create_account(email='cartuser@example.com', username='cartuser', password='Pass1234!'):
    return Account.objects.create_user(email=email, username=username, password=password)


def create_variant(stock=10, price=Decimal('300.00')):
    brand = Brand.objects.create(name='CartBrand')
    category = Category.objects.create(name='CartCategory')
    color = Color.objects.create(name='Red', hex_code='#FF0000')
    product = Product.objects.create(title='Cart Product', description='d', brand=brand, category=category)
    return ProductVariant.objects.create(
        product=product, color=color, price=price, stock=stock, max_quantity_per_user=5
    )


class AddToCartFormTests(TestCase):
    def test_valid_data_passes(self):
        form = AddToCartForm(data={'product_variant_id': 1, 'quantity': 2})
        self.assertTrue(form.is_valid())

    def test_zero_quantity_invalid(self):
        form = AddToCartForm(data={'product_variant_id': 1, 'quantity': 0})
        self.assertFalse(form.is_valid())

    def test_negative_quantity_invalid(self):
        form = AddToCartForm(data={'product_variant_id': 1, 'quantity': -5})
        self.assertFalse(form.is_valid())

    def test_quantity_above_max_invalid(self):
        form = AddToCartForm(data={'product_variant_id': 1, 'quantity': 101})
        self.assertFalse(form.is_valid())

    def test_missing_product_variant_id_invalid(self):
        form = AddToCartForm(data={'quantity': 1})
        self.assertFalse(form.is_valid())

    def test_default_quantity_is_one(self):
        form = AddToCartForm(data={'product_variant_id': 1})
        self.assertFalse(form.is_valid())  # quantity is still required as POST data


class AddToCartViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = create_account()
        self.client.login(email='cartuser@example.com', password='Pass1234!')
        self.variant = create_variant(stock=10)

    def test_add_to_cart_success(self):
        response = self.client.post(reverse('cart:add_to_cart'), {
            'product_variant_id': self.variant.id, 'quantity': 2,
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])

    def test_add_to_cart_invalid_quantity_returns_400(self):
        response = self.client.post(reverse('cart:add_to_cart'), {
            'product_variant_id': self.variant.id, 'quantity': 0,
        })
        self.assertEqual(response.status_code, 400)

    def test_add_to_cart_nonexistent_variant_returns_404(self):
        response = self.client.post(reverse('cart:add_to_cart'), {
            'product_variant_id': 99999, 'quantity': 1,
        })
        self.assertEqual(response.status_code, 404)

    def test_add_to_cart_missing_fields_returns_400(self):
        response = self.client.post(reverse('cart:add_to_cart'), {})
        self.assertEqual(response.status_code, 400)

    def test_add_to_cart_requires_login(self):
        self.client.logout()
        response = self.client.post(reverse('cart:add_to_cart'), {
            'product_variant_id': self.variant.id, 'quantity': 1,
        })
        self.assertEqual(response.status_code, 302)


class PaymentVerifyCsrfTests(TestCase):
    def test_payment_verify_enforces_csrf_protection(self):
        # payment_verify is no longer @csrf_exempt — a POST without a
        # valid CSRF token must now be rejected.
        strict_client = Client(enforce_csrf_checks=True)
        response = strict_client.post(reverse('cart:payment_verify'), {
            'razorpay_payment_id': 'x', 'razorpay_order_id': 'y', 'razorpay_signature': 'z',
        })
        self.assertEqual(response.status_code, 403)