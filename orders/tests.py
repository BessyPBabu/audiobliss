from decimal import Decimal
from django.test import TestCase

from user_log.models import Account, Address, Wallet
from product_management.models import Brand, Category, Product, ProductVariant, Color
from orders.models import Order, OrderProduct
import services.order_service as order_service
import services.payment_service as payment_service
import services.wallet_service as wallet_service


def create_account(email='buyer@example.com', username='buyer'):
    return Account.objects.create_user(email=email, username=username, password='Pass1234!')


def create_address(account):
    return Address.objects.create(
        account=account, house_name='House', streat_name='Street',
        post_office='PO', place='Place', district='District',
        state='State', country='India', pincode='680001',
    )


def create_variant(stock=10, price=Decimal('500.00')):
    brand = Brand.objects.create(name='TestBrand')
    category = Category.objects.create(name='TestCategory')
    color = Color.objects.create(name='Black', hex_code='#000000')
    product = Product.objects.create(title='Test Headphones', description='desc', brand=brand, category=category)
    return ProductVariant.objects.create(
        product=product, color=color, price=price, stock=stock, max_quantity_per_user=5
    )


class FakeCartItem:
    """Lightweight stand-in for cart.models.CartItem so we don't need a real Cart for these tests."""
    def __init__(self, product_variant, quantity, price_at_addition):
        self.product_variant = product_variant
        self.product_variant_id = product_variant.id
        self.quantity = quantity
        self.price_at_addition = price_at_addition


class OrderTotalAmountTests(TestCase):
    def test_total_amount_does_not_double_subtract_discount(self):
        account = create_account()
        address = create_address(account)
        # order_total already reflects the discounted amount, as computed
        # by calculate_order_totals() before Order creation.
        order = Order.objects.create(
            user=account, address=address, order_id='ORD-1',
            order_total=Decimal('450.00'), tax=Decimal('0'),
            coupon_discount=Decimal('50.00'),
        )
        self.assertEqual(order.total_amount, Decimal('450.00'))


class CalculateOrderTotalsTests(TestCase):
    def test_totals_include_service_charge(self):
        totals = order_service.calculate_order_totals(Decimal('1000.00'), Decimal('100.00'))
        self.assertEqual(totals['final_total'], Decimal('900.00'))
        self.assertEqual(
            totals['final_total_with_service_charge'],
            Decimal('900.00') + payment_service.SERVICE_CHARGE,
        )


class CreatePendingOrderStockTests(TestCase):
    def setUp(self):
        self.account = create_account()
        self.address = create_address(self.account)

    def test_creates_order_and_records_coupon_discount(self):
        variant = create_variant(stock=10)
        cart_items = [FakeCartItem(variant, quantity=2, price_at_addition=Decimal('500.00'))]

        order = order_service.create_pending_order(
            user=self.account, address=self.address, cart_items=cart_items,
            order_total=Decimal('935.00'), request_ip='127.0.0.1',
            discount_amount=Decimal('65.00'),
        )

        self.assertEqual(order.coupon_discount, Decimal('65.00'))
        self.assertEqual(OrderProduct.objects.filter(order=order).count(), 1)

    def test_raises_order_error_when_quantity_exceeds_stock(self):
        variant = create_variant(stock=1)
        cart_items = [FakeCartItem(variant, quantity=5, price_at_addition=Decimal('500.00'))]

        with self.assertRaises(order_service.OrderError):
            order_service.create_pending_order(
                user=self.account, address=self.address, cart_items=cart_items,
                order_total=Decimal('2500.00'), request_ip='127.0.0.1',
            )
        # No order should have been persisted on failure (atomic rollback)
        self.assertEqual(Order.objects.count(), 0)

    def test_default_discount_is_zero_when_not_provided(self):
        variant = create_variant(stock=10)
        cart_items = [FakeCartItem(variant, quantity=1, price_at_addition=Decimal('500.00'))]

        order = order_service.create_pending_order(
            user=self.account, address=self.address, cart_items=cart_items,
            order_total=Decimal('565.00'), request_ip='127.0.0.1',
        )
        self.assertEqual(order.coupon_discount, Decimal('0'))


class DecrementStockTests(TestCase):
    def setUp(self):
        self.account = create_account()
        self.address = create_address(self.account)

    def _make_confirmed_order_with_items(self, stock, quantity):
        variant = create_variant(stock=stock)
        order = Order.objects.create(
            user=self.account, address=self.address, order_id='ORD-STOCK',
            order_total=Decimal('500.00'), tax=Decimal('0'),
        )
        OrderProduct.objects.create(
            order=order, user=self.account, product_variant=variant,
            quantity=quantity, product_price=variant.price,
        )
        return order, variant

    def test_decrements_stock_correctly(self):
        order, variant = self._make_confirmed_order_with_items(stock=10, quantity=3)
        payment_service._decrement_stock(order)
        variant.refresh_from_db()
        self.assertEqual(variant.stock, 7)

    def test_raises_when_insufficient_stock_at_confirmation_time(self):
        order, variant = self._make_confirmed_order_with_items(stock=2, quantity=5)
        with self.assertRaises(ValueError):
            payment_service._decrement_stock(order)
        variant.refresh_from_db()
        self.assertEqual(variant.stock, 2)  # unchanged on failure


class OrderCancellationRefundTests(TestCase):
    def setUp(self):
        self.account = create_account()
        self.address = create_address(self.account)
        Wallet.objects.get_or_create(user=self.account)

    def test_confirm_cancellation_refunds_wallet_for_paid_order(self):
        from orders.models import Payment
        payment = Payment.objects.create(
            user=self.account, payment_id='PAY-1', payment_method='Razorpay',
            amount_paid=Decimal('500.00'), status='Completed',
        )
        order = Order.objects.create(
            user=self.account, address=self.address, order_id='ORD-CANCEL',
            order_total=Decimal('500.00'), tax=Decimal('0'), is_ordered=True,
            is_cancel_requested=True, payment=payment,
        )
        order_service.confirm_cancellation(order)
        order.refresh_from_db()
        self.assertEqual(order.status, 'Cancelled')
        self.assertTrue(order.is_refunded)
        self.assertEqual(wallet_service.get_balance(self.account), Decimal('500.00'))

    def test_confirm_cancellation_without_request_raises(self):
        order = Order.objects.create(
            user=self.account, address=self.address, order_id='ORD-NOCANCEL',
            order_total=Decimal('500.00'), tax=Decimal('0'),
        )
        with self.assertRaises(order_service.OrderError):
            order_service.confirm_cancellation(order)