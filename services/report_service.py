import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Sum, Count

logger = logging.getLogger(__name__)


def get_date_range(report_type, start_date_str=None, end_date_str=None):
    today = timezone.now().date()

    if report_type == 'custom' and start_date_str and end_date_str:
        try:
            start = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            return start, end
        except ValueError:
            logger.warning("Invalid custom date range: %s - %s", start_date_str, end_date_str)

    ranges = {
        'daily': (today, today),
        'weekly': (today - timedelta(days=7), today),
        'monthly': (today - timedelta(days=30), today),
        'yearly': (today - timedelta(days=365), today),
    }
    return ranges.get(report_type, (today - timedelta(days=30), today))


def get_orders_for_range(start_date, end_date):
    from orders.models import Order
    return Order.objects.filter(
        created_at__date__range=[start_date, end_date],
        is_ordered=True,
    ).exclude(payment__isnull=True).select_related('user', 'payment').order_by('-created_at')


def calculate_metrics(orders):
    from coupon.models import CouponUsage
    total_count = orders.count()
    total_amount = orders.aggregate(total=Sum('order_total'))['total'] or 0
    order_ids = list(orders.values_list('id', flat=True))
    total_discount = CouponUsage.objects.filter(
        order_id__in=order_ids
    ).aggregate(total=Sum('discount_amount'))['total'] or 0

    return {
        'total_sales_count': total_count,
        'total_order_amount': total_amount,
        'total_discount_amount': total_discount,
    }


def build_order_data(orders_page):
    from orders.models import OrderProduct
    from coupon.models import CouponUsage
    order_data = []

    for order in orders_page:
        usages = CouponUsage.objects.filter(order=order).select_related('coupon')
        coupon_info = (
            ', '.join(f"{u.code} (₹{u.discount_amount})" for u in usages)
            if usages.exists() else "No coupon applied"
        )
        items = OrderProduct.objects.filter(order=order).select_related(
            'product_variant__product', 'product_variant__color'
        )
        item_details = '<br>'.join(
            f"{i.product_variant.product.title} (x{i.quantity}) - ₹{i.product_price}"
            for i in items
        )
        order_data.append({
            'order': order,
            'coupon_info': coupon_info,
            'item_details': item_details,
        })

    return order_data


def get_dashboard_chart_data():
    from orders.models import Order, OrderProduct
    today = timezone.now().date()

    def get_range_data(days):
        start = today - timedelta(days=days)
        return (
            Order.objects.filter(created_at__date__range=[start, today], is_ordered=True)
            .values('created_at__date')
            .annotate(count=Count('id'))
            .order_by('created_at__date')
        )

    daily = get_range_data(6)
    monthly = get_range_data(30)

    yearly = (
        Order.objects.filter(
            created_at__date__range=[today - timedelta(days=365), today], is_ordered=True
        )
        .values('created_at__month')
        .annotate(count=Count('id'))
        .order_by('created_at__month')
    )

    status_data = Order.objects.values('status').annotate(count=Count('id'))

    best_products = (
        OrderProduct.objects.values('product_variant__product__title')
        .annotate(total_quantity=Sum('quantity'))
        .order_by('-total_quantity')[:5]
    )
    best_categories = (
        OrderProduct.objects.values('product_variant__product__category__name')
        .annotate(total_quantity=Sum('quantity'))
        .order_by('-total_quantity')[:5]
    )
    best_brands = (
        OrderProduct.objects.values('product_variant__product__brand__name')
        .annotate(total_quantity=Sum('quantity'))
        .order_by('-total_quantity')[:5]
    )

    return {
        'dates': [d['created_at__date'].strftime('%Y-%m-%d') for d in daily],
        'counts': [d['count'] for d in daily],
        'monthlyDates': [d['created_at__date'].strftime('%Y-%m-%d') for d in monthly],
        'monthlyCounts': [d['count'] for d in monthly],
        'yearlyDates': [
            timezone.datetime(2024, d['created_at__month'], 1).strftime('%B') for d in yearly
        ],
        'yearlyCounts': [d['count'] for d in yearly],
        'statusLabels': [d['status'] for d in status_data],
        'orderCounts': [d['count'] for d in status_data],
        'best_selling_products': best_products,
        'best_selling_categories': best_categories,
        'best_selling_brands': best_brands,
    }
