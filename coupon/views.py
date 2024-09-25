from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Coupon
from .forms import UserCouponForm,CouponForm
from django.contrib.auth.decorators import login_required
from cart.models import Cart
from decimal import Decimal
from django.http import JsonResponse
from django.db import transaction
from .models import Coupon, CouponUsage
from orders.models import Order
from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP



# coupon/views.py

def coupon_list(request):
    coupons = Coupon.objects.all()
    return render(request, 'admin_log/list_coupon.html', {'coupons': coupons})


def add_coupon(request):
    if request.method == 'POST':
        form = CouponForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Coupon added successfully!', extra_tags='success')
            return redirect('coupon:coupon_list')
        else:
            messages.error(request, 'Please correct the errors below.', extra_tags='error')
    else:
        form = CouponForm()
    
    return render(request, 'admin_log/add_coupon.html', {'form': form})

def edit_coupon(request, pk):
    coupon = get_object_or_404(Coupon, pk=pk)
    if request.method == 'POST':
        form = CouponForm(request.POST, instance=coupon)
        if form.is_valid():
            form.save()
            messages.success(request, 'Coupon updated successfully!', extra_tags='success')
            return redirect('coupon:coupon_list')
        else:
            messages.error(request, 'Please correct the errors below.', extra_tags='error')
    else:
        form = CouponForm(instance=coupon)
    
    return render(request, 'admin_log/edit_coupon.html', {'form': form, 'coupon': coupon})

def delete_coupon(request, pk):
    coupon = get_object_or_404(Coupon, pk=pk)
    if request.method == 'POST':
        coupon.delete()
        messages.success(request, 'Coupon deleted successfully!', extra_tags='success')
        return redirect('coupon:coupon_list')
    
    return render(request, 'admin_log/delete_coupon.html', {'coupon': coupon})

@login_required
@transaction.atomic
def apply_coupon(request):
    if request.method == 'POST':
        form = UserCouponForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            print(f"Attempting to apply coupon code: {code}")
            try:
                coupon = Coupon.objects.get(code=code, active=True)
                print(f"Coupon found: {coupon}")
                cart = Cart.objects.get(user=request.user)
                
                # Calculate cart total
                cart_total = sum(item.subtotal for item in cart.items.all())
                print(f"Cart total: {cart_total}")

                # Check if minimum purchase amount condition is met
                if coupon.min_purchase_amount and cart_total < coupon.min_purchase_amount:
                    messages.error(request, f'Coupon requires a minimum purchase of ₹{coupon.min_purchase_amount}.')
                else:
                   # Calculate the discount amount
                    if coupon.discount_type == 'percentage':
                        discount_amount = (cart_total * Decimal(coupon.discount_value) / Decimal(100)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                        print(f"Percentage discount: {coupon.discount_value}% = {discount_amount}")
                    else:  # Assuming 'FIXED' discount type
                        discount_amount = min(Decimal(coupon.discount_value), cart_total).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                        print(f"Fixed discount: {discount_amount}")
                    
                    # Calculate the final order total
                    order_total = (cart_total - discount_amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    print(f"Order total after discount: {order_total}")
                    
                    # Store coupon details in session
                    request.session['coupon'] = {
                        'code': coupon.code,
                        'discount_type': coupon.discount_type,
                        'discount_value': str(coupon.discount_value),
                        'discount_amount': str(discount_amount),
                        'cart_total_at_application': str(cart_total)
                    }
                    print(f"Coupon data stored in session: {request.session['coupon']}")

                    # Fetch or create the most recent uncompleted order for the user
                    order, created = Order.objects.get_or_create(
                        user=request.user, 
                        is_ordered=False,
                        defaults={
                            'created_at': timezone.now(),
                            'order_total': Decimal(order_total)
                        }   
                    )
                    print(f"Order {'created' if created else 'updated'}: {order}")

                    # If the order already existed, update its total
                    if not created:
                        order.order_total = Decimal(order_total)
                        order.save()
                        print(f"Existing order updated with new total: {order_total}")
                    

                    # Record the coupon usage associated with this order
                    coupon_usage = CouponUsage.objects.create(
                        order=order,
                        coupon=coupon,
                        code=coupon.code,
                        discount_amount=Decimal(discount_amount)
                    )
                    print(f"CouponUsage record created: {coupon_usage}")


                    messages.success(request, 'Coupon applied successfully!')
            except Coupon.DoesNotExist:
                messages.error(request, 'Invalid or expired coupon code.')
        else:
            messages.error(request, 'Invalid form submission.')
    return redirect('cart:cart_checkout')