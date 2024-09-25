from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from user_log.forms import AddressForm 
from cart.models import Cart, CartItem
from .models import Order,OrderProduct
from .forms import OrderForm
from coupon.models import Coupon, CouponUsage
from product_management.models import ProductVariant
import uuid
from django.db import transaction
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from decimal import Decimal

# Create your views here.


@login_required
def success(request):
    # Get the latest order of the logged-in user
    latest_order = Order.objects.filter(user=request.user).order_by('-created_at').first()
    
    if latest_order:
        # Check if there is a coupon in the session
        if 'coupon' in request.session:
            coupon_data = request.session['coupon']
            coupon_code = coupon_data.get('code')
            
            if coupon_code:
                try:
                    coupon = Coupon.objects.get(code=coupon_code)
                    
                    # Save the coupon usage for the latest order
                    CouponUsage.objects.create(
                        order=latest_order,
                        coupon=coupon,
                        code=coupon.code,
                        discount_amount=Decimal(coupon_data.get('discount_amount', '0'))
                    )
                    
                    messages.success(request, f'Coupon "{coupon_code}" has been applied to your order.')
                except Coupon.DoesNotExist:
                    messages.error(request, f'Coupon "{coupon_code}" not found.')
            else:
                messages.warning(request, 'Invalid coupon data in session.')
            
            # Clear the coupon from the session
            del request.session['coupon']
            request.session.modified = True
            
            messages.info(request, 'Coupon has been cleared for your next order.')
        else:
            messages.info(request, 'No coupon was applied to this order.')
    else:
        messages.warning(request, 'No recent order found.')

    return render(request, 'user_log/success.html', {'latest_order': latest_order})

@login_required
def invoice(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = OrderProduct.objects.filter(order=order)

    # Calculate total price for each item using price_at_addition
    for item in order_items:
        item.total_price = item.product_price * item.quantity

    context = {
        'order': order,
        'order_items': order_items,
    }
    # Check if user wants to download PDF
    if request.GET.get('download') == 'pdf':
        template_path = 'user_log/invoice.html'
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{order.id}.pdf"'

        # Render the HTML into a PDF
        template = get_template(template_path)
        html = template.render(context)
        pisa_status = pisa.CreatePDF(html, dest=response)

        # If error in PDF generation, show the error
        if pisa_status.err:
            return HttpResponse(f'Error generating PDF: {pisa_status.err}')
        return response



    return render(request, 'user_log/invoice.html', context)

# Utility Functions
def calculate_order_total(user):
    cart_items = get_cart_items(user)
    total = sum(item['quantity'] * item['price'] for item in cart_items)
    return total

def get_cart_items(user):
    cart = get_object_or_404(Cart, user=user)
    cart_items = CartItem.objects.filter(cart=cart)
    return [
        {
            'variant_id': item.product_variant.id,
            'quantity': item.quantity,
            'price': item.product_variant.price
        }
        for item in cart_items
    ]


