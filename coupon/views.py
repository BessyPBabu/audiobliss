import logging
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404

import services.coupon_service as coupon_service
from .forms import CouponForm, UserCouponForm
from .models import Coupon

logger = logging.getLogger(__name__)


def coupon_list(request):
    coupons = Coupon.objects.all().order_by('-id')
    return render(request, 'admin_log/list_coupon.html', {'coupons': coupons})


def add_coupon(request):
    if request.method == 'POST':
        form = CouponForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Coupon added successfully.")
                return redirect('coupon:coupon_list')
            except Exception:
                logger.exception("Error adding coupon")
                messages.error(request, "Failed to add coupon.")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CouponForm()

    return render(request, 'admin_log/add_coupon.html', {'form': form})


def edit_coupon(request, pk):
    coupon = get_object_or_404(Coupon, pk=pk)
    if request.method == 'POST':
        form = CouponForm(request.POST, instance=coupon)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Coupon updated successfully.")
                return redirect('coupon:coupon_list')
            except Exception:
                logger.exception("Error updating coupon %s", pk)
                messages.error(request, "Failed to update coupon.")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CouponForm(instance=coupon)

    return render(request, 'admin_log/edit_coupon.html', {'form': form, 'coupon': coupon})


def delete_coupon(request, pk):
    coupon = get_object_or_404(Coupon, pk=pk)
    if request.method == 'POST':
        try:
            coupon.delete()
            messages.success(request, "Coupon deleted successfully.")
        except Exception:
            logger.exception("Error deleting coupon %s", pk)
            messages.error(request, "Failed to delete coupon.")
        return redirect('coupon:coupon_list')

    return render(request, 'admin_log/delete_coupon.html', {'coupon': coupon})


@login_required
@transaction.atomic
def apply_coupon(request):
    if request.method != 'POST':
        return redirect('cart:cart_checkout')

    form = UserCouponForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Invalid coupon code.")
        return redirect('cart:cart_checkout')

    code = form.cleaned_data['code']

    try:
        from cart.models import Cart
        cart = Cart.objects.get(user=request.user)
        cart_total = cart.get_total()

        coupon = coupon_service.validate_coupon_for_cart(code, cart_total)
        discount = coupon_service.calculate_discount(coupon, cart_total)
        coupon_service.store_coupon_in_session(request, coupon, discount, cart_total)

        messages.success(request, f"Coupon applied! You save ₹{discount}.")
        logger.info("Coupon %s applied for user %s", code, request.user.id)

    except Cart.DoesNotExist:
        messages.error(request, "Your cart is empty.")
    except coupon_service.CouponError as e:
        messages.error(request, str(e))
    except Exception:
        logger.exception("Unexpected error applying coupon %s for user %s", code, request.user.id)
        messages.error(request, "Failed to apply coupon. Please try again.")

    return redirect('cart:cart_checkout')
