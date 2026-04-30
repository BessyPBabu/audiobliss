import logging
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import get_template

from xhtml2pdf import pisa

from .models import Order, OrderProduct

logger = logging.getLogger(__name__)


@login_required
def success(request):
    # Coupon usage is recorded in coupon/views.py apply_coupon — not here
    # to avoid duplicate records
    latest_order = Order.objects.filter(
        user=request.user, is_ordered=True
    ).order_by('-created_at').first()

    return render(request, 'user_log/success.html', {'latest_order': latest_order})


@login_required
def invoice(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = OrderProduct.objects.filter(order=order).select_related(
        'product_variant__product', 'product_variant__color'
    )

    for item in order_items:
        # Use price at order time, not current product price
        item.total_price = item.product_price * item.quantity

    context = {'order': order, 'order_items': order_items}

    if request.GET.get('download') == 'pdf':
        try:
            template = get_template('user_log/invoice.html')
            html = template.render(context)
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="invoice_{order.id}.pdf"'
            pisa_status = pisa.CreatePDF(html, dest=response)
            if pisa_status.err:
                logger.error("PDF generation error for order %s: %s", order.id, pisa_status.err)
                return HttpResponse("Error generating PDF. Please try again.")
            return response
        except Exception:
            logger.exception("Unexpected error generating PDF for order %s", order.id)
            return HttpResponse("Error generating PDF. Please try again.")

    return render(request, 'user_log/invoice.html', context)
