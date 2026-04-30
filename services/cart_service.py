import logging
from decimal import Decimal
from django.db import transaction

from services.offer_service import get_discounted_price_for_variant

logger = logging.getLogger(__name__)


class CartError(Exception):
    pass


def get_or_create_cart(user):
    from cart.models import Cart
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


def get_cart_total(cart):
    return sum(item.subtotal for item in cart.items.select_related('product_variant').all())


def add_item(user, product_variant, quantity=1):
    from cart.models import CartItem

    if quantity <= 0:
        raise CartError("Quantity must be at least 1.")

    if product_variant.stock < quantity:
        raise CartError(f"Only {product_variant.stock} units available in stock.")

    cart = get_or_create_cart(user)

    with transaction.atomic():
        cart_item, created = CartItem.objects.select_for_update().get_or_create(
            cart=cart,
            product_variant=product_variant,
            defaults={'quantity': 0, 'price_at_addition': Decimal('0')},
        )

        new_quantity = cart_item.quantity + quantity
        if new_quantity > product_variant.max_quantity_per_user:
            raise CartError(
                f"Maximum {product_variant.max_quantity_per_user} units per user allowed."
            )

        discounted_price = get_discounted_price_for_variant(product_variant)
        cart_item.quantity = new_quantity
        cart_item.price_at_addition = discounted_price
        cart_item.save(update_fields=['quantity', 'price_at_addition'])
        logger.info("Added %s x variant %s to cart for user %s", quantity, product_variant.id, user.id)

    return cart_item


def remove_item(user, cart_item_id):
    from cart.models import CartItem
    try:
        item = CartItem.objects.get(id=cart_item_id, cart__user=user)
        item.delete()
        logger.info("Removed cart item %s for user %s", cart_item_id, user.id)
    except CartItem.DoesNotExist:
        raise CartError("Cart item not found.")


def update_quantity(user, cart_item_id, new_quantity):
    from cart.models import CartItem

    if new_quantity < 1:
        raise CartError("Quantity must be at least 1.")

    try:
        item = CartItem.objects.select_related('product_variant').get(
            id=cart_item_id, cart__user=user
        )
    except CartItem.DoesNotExist:
        raise CartError("Cart item not found.")

    variant = item.product_variant
    if new_quantity > variant.max_quantity_per_user:
        raise CartError(f"Maximum {variant.max_quantity_per_user} units per user allowed.")

    if new_quantity > variant.stock:
        raise CartError(f"Only {variant.stock} units available in stock.")

    item.quantity = new_quantity
    item.save(update_fields=['quantity'])
    logger.info("Updated cart item %s to quantity %s", cart_item_id, new_quantity)
    return item


def clear_cart(user):
    cart = get_or_create_cart(user)
    deleted, _ = cart.items.all().delete()
    logger.info("Cleared %s items from cart for user %s", deleted, user.id)


def get_cart_context(user):
    cart = get_or_create_cart(user)
    cart_items = cart.items.select_related(
        'product_variant__product', 'product_variant__color'
    ).all()
    total = get_cart_total(cart)
    return cart, cart_items, total
