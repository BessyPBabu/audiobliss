import logging
from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone

logger = logging.getLogger(__name__)


class CouponError(Exception):
    pass


def get_active_coupon(code):
    from apps.coupon.models import Coupon
    try:
        coupon = Coupon.objects.get(code=code, active=True)
        if not coupon.is_valid():
            raise CouponError("Coupon has expired.")
        return coupon
    except Coupon.DoesNotExist:
        raise CouponError("Invalid or expired coupon code.")


def validate_coupon_for_cart(code, cart_total):
    coupon = get_active_coupon(code)
    cart_total = Decimal(str(cart_total))

    if coupon.min_purchase_amount and cart_total < coupon.min_purchase_amount:
        raise CouponError(
            f"Minimum purchase of ₹{coupon.min_purchase_amount} required for this coupon."
        )
    return coupon


def calculate_discount(coupon, cart_total):
    cart_total = Decimal(str(cart_total))
    if coupon.discount_type == 'percentage':
        discount = (cart_total * coupon.discount_value / Decimal('100')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
    else:
        discount = min(coupon.discount_value, cart_total).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
    logger.debug("Coupon %s discount: ₹%s on cart total ₹%s", coupon.code, discount, cart_total)
    return discount


def store_coupon_in_session(request, coupon, discount_amount, cart_total):
    request.session['coupon'] = {
        'code': coupon.code,
        'discount_type': coupon.discount_type,
        'discount_value': str(coupon.discount_value),
        'discount_amount': str(discount_amount),
        'cart_total_at_application': str(cart_total),
    }
    request.session.modified = True


def get_session_coupon_discount(request, current_cart_total):
    coupon_data = request.session.get('coupon')
    if not coupon_data:
        return Decimal('0.00'), None

    current_cart_total = Decimal(str(current_cart_total))
    stored_cart_total = Decimal(coupon_data['cart_total_at_application'])

    if stored_cart_total != current_cart_total:
        # Recalculate if cart changed
        if coupon_data['discount_type'] == 'percentage':
            discount = (
                current_cart_total * Decimal(coupon_data['discount_value']) / Decimal('100')
            ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        else:
            discount = min(Decimal(coupon_data['discount_value']), current_cart_total).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
    else:
        discount = Decimal(coupon_data['discount_amount'])

    return discount, coupon_data


def clear_session_coupon(request):
    request.session.pop('coupon', None)
    request.session.modified = True


def record_coupon_usage(order, coupon, discount_amount):
    from apps.coupon.models import CouponUsage
    # Guard against duplicates
    if CouponUsage.objects.filter(order=order, coupon=coupon).exists():
        logger.warning("Coupon usage already recorded for order %s", order.id)
        return
    CouponUsage.objects.create(
        order=order,
        coupon=coupon,
        code=coupon.code,
        discount_amount=Decimal(str(discount_amount)),
    )
    logger.info("Recorded coupon %s usage for order %s", coupon.code, order.id)
