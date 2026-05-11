import logging
from decimal import Decimal
from django.conf import settings
from django.db import transaction
from django.urls import reverse

import razorpay

logger = logging.getLogger(__name__)

SERVICE_CHARGE = Decimal('65')


def get_razorpay_client():
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def create_razorpay_order(amount_inr):
    client = get_razorpay_client()
    amount_paise = int(Decimal(str(amount_inr)) * 100)
    razorpay_order = client.order.create({
        'amount': amount_paise,
        'currency': 'INR',
        'payment_capture': '0',
    })
    logger.info("Created Razorpay order %s for ₹%s", razorpay_order['id'], amount_inr)
    return razorpay_order


def verify_razorpay_signature(payment_id, order_id, signature):
    client = get_razorpay_client()
    params = {
        'razorpay_order_id': order_id,
        'razorpay_payment_id': payment_id,
        'razorpay_signature': signature,
    }
    # Raises razorpay.errors.SignatureVerificationError on failure
    client.utility.verify_payment_signature(params)
    logger.info("Verified Razorpay signature for order %s", order_id)


def process_wallet_payment(request, order, total_amount):
    from orders.models import Payment
    import services.wallet_service as wallet_service

    total_amount = Decimal(str(total_amount))
    balance = wallet_service.get_balance(request.user)

    with transaction.atomic():
        if balance >= total_amount:
            wallet_service.debit(request.user, total_amount)
            payment = Payment.objects.create(
                user=request.user,
                payment_id=f'WALLET_{order.order_id}',
                payment_method='Wallet',
                amount_paid=total_amount,
                status='Completed',
            )
            _confirm_order(order, payment)
            logger.info("Full wallet payment for order %s", order.order_id)
            return {'type': 'redirect', 'url': 'orders:success'}

        # Partial wallet payment — remainder via Razorpay
        amount_from_wallet = balance
        amount_from_razorpay = total_amount - amount_from_wallet

        wallet_service.debit(request.user, amount_from_wallet)

        razorpay_order = create_razorpay_order(amount_from_razorpay)
        order.razorpay_order_id = razorpay_order['id']
        order.save(update_fields=['razorpay_order_id'])

        logger.info(
            "Partial wallet (₹%s) + Razorpay (₹%s) for order %s",
            amount_from_wallet, amount_from_razorpay, order.order_id,
        )
        return {
            'type': 'render',
            'template': 'user_log/razorpay_payment.html',
            'context': _razorpay_context(request, order, razorpay_order, amount_from_razorpay),
        }


def process_razorpay_payment(request, order, total_amount):
    razorpay_order = create_razorpay_order(total_amount)
    order.razorpay_order_id = razorpay_order['id']
    order.save(update_fields=['razorpay_order_id'])
    logger.info("Razorpay payment initiated for order %s", order.order_id)
    return {
        'type': 'render',
        'template': 'user_log/razorpay_payment.html',
        'context': _razorpay_context(request, order, razorpay_order, total_amount),
    }


def process_cod_payment(order, total_amount, cart_items):
    from orders.models import Payment, OrderProduct
    with transaction.atomic():
        payment = Payment.objects.create(
            user=order.user,
            payment_id=f'COD_{order.order_id}',
            payment_method='Cash On Delivery',
            amount_paid=Decimal(str(total_amount)),
            status='Pending',
        )
        _confirm_order(order, payment)
        _decrement_stock(order)
        cart_items.delete()
        logger.info("COD order confirmed: %s", order.order_id)
    return {'type': 'redirect', 'url': 'orders:success'}


def confirm_razorpay_payment(razorpay_payment_id, razorpay_order_id, razorpay_signature):
    from orders.models import Order, Payment, OrderProduct
    import services.wallet_service as wallet_service

    verify_razorpay_signature(razorpay_payment_id, razorpay_order_id, razorpay_signature)

    with transaction.atomic():
        try:
            order = Order.objects.select_for_update().get(razorpay_order_id=razorpay_order_id)
        except Order.DoesNotExist:
            raise ValueError(f"Order not found for Razorpay order {razorpay_order_id}")

        if order.is_ordered:
            logger.warning("Order %s already processed", order.order_id)
            return order

        client = get_razorpay_client()
        rz_payment = client.payment.fetch(razorpay_payment_id)
        razorpay_amount = Decimal(str(rz_payment['amount'])) / 100

        payment = Payment.objects.create(
            user=order.user,
            payment_id=razorpay_payment_id,
            payment_method='Razorpay',
            amount_paid=razorpay_amount,
            status='Completed',
        )
        _confirm_order(order, payment)
        _decrement_stock(order)

        from cart.models import Cart
        Cart.objects.filter(user=order.user).delete()

        logger.info("Razorpay payment confirmed for order %s", order.order_id)
    return order


def _confirm_order(order, payment):
    from orders.models import OrderProduct
    order.is_ordered = True
    order.payment = payment
    order.payment_status = 'Completed'
    order.status = 'Confirmed'
    order.save(update_fields=['is_ordered', 'payment', 'payment_status', 'status'])
    OrderProduct.objects.filter(order=order).update(ordered=True)


def _decrement_stock(order):
    from orders.models import OrderProduct
    items = OrderProduct.objects.filter(order=order).select_related('product_variant')
    for item in items:
        variant = item.product_variant
        if variant.stock < item.quantity:
            logger.error(
                "Insufficient stock for variant %s during order %s confirmation",
                variant.id, order.order_id,
            )
            raise ValueError(f"Insufficient stock for {variant.product.title}")
        variant.stock -= item.quantity
        variant.save(update_fields=['stock'])


def _razorpay_context(request, order, razorpay_order, amount):
    return {
        'order': order,
        'razorpay_order_id': razorpay_order['id'],
        'razorpay_merchant_key': settings.RAZORPAY_KEY_ID,
        'razorpay_amount': int(Decimal(str(amount)) * 100),
        'currency': 'INR',
        'callback_url': request.build_absolute_uri(reverse('cart:payment_verify')),
    }
