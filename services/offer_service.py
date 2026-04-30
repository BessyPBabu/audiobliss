import logging
from decimal import Decimal
from django.utils import timezone

logger = logging.getLogger(__name__)


def get_best_offer_for_product(product):
    from offer_management.models import ProductOffer, CategoryOffer
    now = timezone.now()

    product_offers = ProductOffer.objects.filter(
        product=product,
        offer__is_active=True,
        offer__start_date__lte=now,
        offer__end_date__gte=now,
    ).select_related('offer')

    category_offers = CategoryOffer.objects.filter(
        category=product.category,
        offer__is_active=True,
        offer__start_date__lte=now,
        offer__end_date__gte=now,
    ).select_related('offer')

    best_discount = Decimal('0')
    best_offer = None

    for po in product_offers:
        if po.offer.discount_percentage > best_discount:
            best_discount = po.offer.discount_percentage
            best_offer = po

    for co in category_offers:
        if co.offer.discount_percentage > best_discount:
            best_discount = co.offer.discount_percentage
            best_offer = co

    return best_offer


def apply_offer_to_price(price, offer):
    price = Decimal(str(price))
    if offer is None:
        return price
    if not offer.offer.is_valid():
        return price
    discount = price * (offer.offer.discount_percentage / Decimal('100'))
    discounted = (price - discount).quantize(Decimal('0.01'))
    logger.debug("Applied offer %s: ₹%s -> ₹%s", offer.offer.name, price, discounted)
    return discounted


def get_discounted_price_for_variant(variant):
    offer = get_best_offer_for_product(variant.product)
    return apply_offer_to_price(variant.price, offer)


def get_discount_percentage_for_product(product):
    offer = get_best_offer_for_product(product)
    if offer is None:
        return Decimal('0')
    return offer.offer.discount_percentage
