import logging
from decimal import Decimal
from django.db.models import Min, Max, Q, F, Value, Subquery, OuterRef, ExpressionWrapper, DecimalField
from django.db.models.functions import Coalesce, Greatest
from django.utils import timezone
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

logger = logging.getLogger(__name__)

PRODUCTS_PER_PAGE = 6


def get_annotated_products_queryset():
    from apps.products.models import Product
    from apps.offers.models import ProductOffer, CategoryOffer
    now = timezone.now()

    return Product.objects.filter(deleted=False, is_active=True).annotate(
        product_discount=Subquery(
            ProductOffer.objects.filter(
                product=OuterRef('pk'),
                offer__is_active=True,
                offer__start_date__lte=now,
                offer__end_date__gte=now,
            ).order_by('-offer__discount_percentage').values('offer__discount_percentage')[:1]
        ),
        product_offer_name=Subquery(
            ProductOffer.objects.filter(
                product=OuterRef('pk'),
                offer__is_active=True,
                offer__start_date__lte=now,
                offer__end_date__gte=now,
            ).order_by('-offer__discount_percentage').values('offer__name')[:1]
        ),
        category_discount=Subquery(
            CategoryOffer.objects.filter(
                category=OuterRef('category'),
                offer__is_active=True,
                offer__start_date__lte=now,
                offer__end_date__gte=now,
            ).order_by('-offer__discount_percentage').values('offer__discount_percentage')[:1]
        ),
        category_offer_name=Subquery(
            CategoryOffer.objects.filter(
                category=OuterRef('category'),
                offer__is_active=True,
                offer__start_date__lte=now,
                offer__end_date__gte=now,
            ).order_by('-offer__discount_percentage').values('offer__name')[:1]
        ),
        best_discount=Greatest(
            Coalesce(F('product_discount'), Value(0, output_field=DecimalField())),
            Coalesce(F('category_discount'), Value(0, output_field=DecimalField())),
            output_field=DecimalField(),
        ),
        min_variant_price=Min('variants__price'),
        discounted_price=ExpressionWrapper(
            F('min_variant_price') * (1 - F('best_discount') / 100),
            output_field=DecimalField(max_digits=10, decimal_places=2),
        ),
    ).select_related('category', 'brand').prefetch_related('variants')


def apply_filters(queryset, search_query=None, category_name=None, sort_by='featured'):
    if search_query:
        queryset = queryset.filter(
            Q(title__icontains=search_query) | Q(category__name__icontains=search_query)
        )

    if category_name:
        queryset = queryset.filter(category__name=category_name)

    sort_map = {
        'name_asc': 'title',
        'name_desc': '-title',
        'price_asc': 'min_variant_price',
        'price_desc': '-min_variant_price',
    }
    order_field = sort_map.get(sort_by, 'id')
    queryset = queryset.order_by(order_field)

    return queryset.distinct()


def paginate_queryset(queryset, page, per_page=PRODUCTS_PER_PAGE):
    paginator = Paginator(queryset, per_page)
    try:
        return paginator.page(page)
    except PageNotAnInteger:
        return paginator.page(1)
    except EmptyPage:
        return paginator.page(paginator.num_pages)


def enrich_products_with_offer_data(products):
    for product in products:
        variant = product.variants.filter(is_active=True).first()
        if variant and product.min_variant_price is not None:
            product.original_price = Decimal(str(product.min_variant_price)).quantize(Decimal('0.01'))
            product.computed_discounted_price = Decimal(str(product.discounted_price)).quantize(Decimal('0.01'))
            if product.best_discount > 0:
                product.active_offer = {
                    'discount_percentage': product.best_discount,
                    'name': product.product_offer_name or product.category_offer_name,
                }
            else:
                product.active_offer = None
        else:
            product.original_price = None
            product.computed_discounted_price = None
            product.active_offer = None
    return products


def soft_delete_product(product):
    product.deleted = True
    product.is_active = False
    product.save(update_fields=['deleted', 'is_active'])
    product.variants.filter(deleted=False).update(deleted=True, is_active=False)
    logger.info("Soft deleted product %s and its variants", product.id)


def soft_delete_variant(variant):
    variant.deleted = True
    variant.is_active = False
    variant.save(update_fields=['deleted', 'is_active'])
    logger.info("Soft deleted variant %s", variant.id)
