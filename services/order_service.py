import logging
import uuid
from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction

from services.payment_service import SERVICE_CHARGE

logger = logging.getLogger(__name__)


class OrderError(Exception):
    pass


def calculate_order_totals(cart_total, discount_amount=Decimal('0')):
    cart_total = Decimal(str(cart_total))
    discount_amount = Decimal(str(discount_amount))
    final_total = (cart_total - discount_amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    final_with_service = (final_total + SERVICE_CHARGE).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return {
        'cart_total': cart_total,
        'discount_amount': discount_amount,
        'final_total': final_total,
        'service_charge': SERVICE_CHARGE,
        'final_total_with_service_charge': final_with_service,
    }


def create_pending_order(user, address, cart_items, order_total, request_ip):
    from orders.models import Order, OrderProduct

    with transaction.atomic():
        # Validate stock before creating order
        for item in cart_items:
            if item.quantity > item.product_variant.stock:
                raise OrderError(
                    f"'{item.product_variant.product.title}' has only "
                    f"{item.product_variant.stock} units in stock."
                )

        order = Order.objects.create(
            user=user,
            address=address,
            order_id=str(uuid.uuid4()),
            order_total=Decimal(str(order_total)),
            tax=Decimal('0'),
            ip=request_ip,
            is_ordered=False,
            status='New',
        )

        order_products = [
            OrderProduct(
                order=order,
                user=user,
                product_variant=item.product_variant,
                quantity=item.quantity,
                product_price=item.price_at_addition,
                ordered=False,
            )
            for item in cart_items
        ]
        OrderProduct.objects.bulk_create(order_products)
        logger.info("Created pending order %s for user %s", order.order_id, user.id)

    return order


def request_cancellation(order, reason):
    if order.status not in ('New', 'Confirmed'):
        raise OrderError(f"Cannot cancel order with status '{order.status}'.")

    order.cancel_reason = reason
    order.is_cancel_requested = True
    order.status = 'Pending Cancellation'
    order.save(update_fields=['cancel_reason', 'is_cancel_requested', 'status'])
    logger.info("Cancellation requested for order %s, reason: %s", order.order_id, reason)


def confirm_cancellation(order):
    import services.wallet_service as wallet_service

    if not order.is_cancel_requested:
        raise OrderError("No cancellation request found for this order.")

    with transaction.atomic():
        order.status = 'Cancelled'
        order.is_cancel_confirmed = True
        order.save(update_fields=['status', 'is_cancel_confirmed'])

        if order.is_ordered and not order.is_refunded and order.payment:
            if order.payment.payment_method in ('Razorpay', 'Wallet'):
                wallet_service.credit(order.user, order.order_total)
                order.is_refunded = True
                order.save(update_fields=['is_refunded'])
                logger.info("Refund of ₹%s issued for cancelled order %s", order.order_total, order.order_id)


def request_return(order, user, reason):
    from orders.models import ReturnRequest

    if order.status != 'Delivered':
        raise OrderError("Only delivered orders can be returned.")

    if ReturnRequest.objects.filter(order=order).exists():
        raise OrderError("A return request already exists for this order.")

    with transaction.atomic():
        return_request = ReturnRequest.objects.create(
            order=order,
            user=user,
            reason=reason,
            status='Pending',
        )
        order.status = 'Return Requested'
        order.save(update_fields=['status'])
        logger.info("Return requested for order %s by user %s", order.order_id, user.id)

    return return_request


def approve_return(return_request):
    import services.wallet_service as wallet_service

    if return_request.status != 'Pending':
        raise OrderError(f"Return request is already {return_request.status}.")

    with transaction.atomic():
        order = return_request.order
        wallet_service.credit(order.user, order.order_total)

        return_request.status = 'Approved'
        return_request.refunded = True
        return_request.save(update_fields=['status', 'refunded'])

        order.status = 'Returned'
        order.is_refunded = True
        order.save(update_fields=['status', 'is_refunded'])
        logger.info("Approved return for order %s, refunded ₹%s", order.order_id, order.order_total)


def reject_return(return_request):
    if return_request.status != 'Pending':
        raise OrderError(f"Return request is already {return_request.status}.")

    return_request.status = 'Rejected'
    return_request.save(update_fields=['status'])
    logger.info("Rejected return request %s", return_request.id)
