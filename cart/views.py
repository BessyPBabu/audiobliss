import logging
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET

import services.cart_service as cart_service
import services.coupon_service as coupon_service
import services.payment_service as payment_service
import services.order_service as order_service
from .models import Cart, CartItem, Wishlist, WishlistItem
from user_log.models import Address
from user_log.forms import AddressForm
from coupon.forms import UserCouponForm

logger = logging.getLogger(__name__)


# ─── Cart ─────────────────────────────────────────────────────────────────────

@login_required
def view_cart(request):
    cart, cart_items, total = cart_service.get_cart_context(request.user)
    return render(request, 'user_log/cart.html', {'cart_items': cart_items, 'total': total})


@login_required
@require_POST
def add_to_cart(request):
    product_variant_id = request.POST.get('product_variant_id', '').strip()

    if not product_variant_id or not product_variant_id.isdigit():
        return JsonResponse({'success': False, 'error': 'Invalid product variant.'}, status=400)

    from product_management.models import ProductVariant
    try:
        variant = ProductVariant.objects.get(id=int(product_variant_id), is_active=True, deleted=False)
    except ProductVariant.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Product variant not found.'}, status=404)

    try:
        quantity = int(request.POST.get('quantity', 1))
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Invalid quantity.'}, status=400)

    try:
        cart_service.add_item(request.user, variant, quantity)
        cart = cart_service.get_or_create_cart(request.user)
        cart_total = cart_service.get_cart_total(cart)
        return JsonResponse({
            'success': True,
            'cart_total': str(cart_total),
            'item_count': cart.get_item_count(),
        })
    except cart_service.CartError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception:
        logger.exception("Unexpected error adding to cart for user %s", request.user.id)
        return JsonResponse({'success': False, 'error': 'An error occurred.'}, status=500)


@login_required
def remove_from_cart(request, cart_item_id):
    try:
        cart_service.remove_item(request.user, cart_item_id)
        cart = cart_service.get_or_create_cart(request.user)
        cart_total = cart_service.get_cart_total(cart)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'cart_total': str(cart_total),
                'cart_count': cart.get_item_count(),
            })
        messages.success(request, "Item removed from cart.")
    except cart_service.CartError as e:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
        messages.error(request, str(e))
    except Exception:
        logger.exception("Error removing cart item %s", cart_item_id)
        messages.error(request, "Failed to remove item.")

    return redirect('cart:view_cart')


@login_required
@require_POST
def update_cart(request, cart_item_id):
    try:
        new_quantity = int(request.POST.get('quantity', 1))
    except ValueError:
        return JsonResponse({'error': 'Invalid quantity.'}, status=400)

    try:
        item = cart_service.update_quantity(request.user, cart_item_id, new_quantity)
        cart = cart_service.get_or_create_cart(request.user)
        return JsonResponse({
            'success': True,
            'item_subtotal': str(item.subtotal),
            'cart_total': str(cart_service.get_cart_total(cart)),
            'cart_count': cart.get_item_count(),
        })
    except cart_service.CartError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception:
        logger.exception("Error updating cart item %s", cart_item_id)
        return JsonResponse({'success': False, 'error': 'An error occurred.'}, status=500)


@login_required
@require_POST
def clear_cart(request):
    try:
        cart_service.clear_cart(request.user)
        messages.success(request, "Cart cleared.")
    except Exception:
        logger.exception("Error clearing cart for user %s", request.user.id)
        messages.error(request, "Failed to clear cart.")
    return redirect('cart:view_cart')


# ─── Checkout ─────────────────────────────────────────────────────────────────

@login_required
def cart_checkout(request):
    from coupon.models import Coupon

    try:
        cart, cart_items, cart_total = cart_service.get_cart_context(request.user)
    except Exception:
        logger.exception("Error loading cart for checkout, user %s", request.user.id)
        messages.error(request, "Failed to load cart.")
        return redirect('cart:view_cart')

    if not cart_items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect('cart:view_cart')

    from user_log.models import Wallet
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    addresses = Address.objects.filter(account=request.user)

    if not addresses.exists():
        messages.info(request, "Please add a delivery address first.")
        return redirect('userlog:user_profile')

    default_address = request.user.get_default_address()
    discount_amount, _ = coupon_service.get_session_coupon_discount(request, cart_total)
    totals = order_service.calculate_order_totals(cart_total, discount_amount)
    active_coupons = Coupon.objects.filter(active=True)

    if request.method == 'POST':
        address_id = request.POST.get('address')
        payment_method = request.POST.get('payment_option')

        if not address_id:
            messages.error(request, "Please select a delivery address.")
            return redirect('cart:cart_checkout')

        address = get_object_or_404(Address, id=address_id, account=request.user)

        try:
            pending_order = order_service.create_pending_order(
                user=request.user,
                address=address,
                cart_items=cart_items,
                order_total=totals['final_total_with_service_charge'],
                request_ip=request.META.get('REMOTE_ADDR', ''),
            )
        except order_service.OrderError as e:
            messages.error(request, str(e))
            return redirect('cart:cart_checkout')
        except Exception:
            logger.exception("Error creating order for user %s", request.user.id)
            messages.error(request, "Failed to place order. Please try again.")
            return redirect('cart:cart_checkout')

        try:
            if payment_method == 'Wallet':
                result = payment_service.process_wallet_payment(
                    request, pending_order, totals['final_total_with_service_charge']
                )
            elif payment_method == 'Razorpay':
                result = payment_service.process_razorpay_payment(
                    request, pending_order, totals['final_total_with_service_charge']
                )
            else:
                result = payment_service.process_cod_payment(
                    pending_order, totals['final_total_with_service_charge'], cart_items
                )

            if result['type'] == 'redirect':
                return redirect(result['url'])
            return render(request, result['template'], result['context'])

        except Exception:
            logger.exception("Payment processing error for order %s", pending_order.order_id)
            pending_order.delete()
            messages.error(request, "Payment failed. Please try again.")
            return redirect('cart:cart_checkout')

    return render(request, 'user_log/cart_checkout.html', {
        'cart': cart,
        'cart_items': cart_items,
        'addresses': addresses,
        'default_address': default_address,
        'active_coupons': active_coupons,
        'coupon_form': UserCouponForm(),
        'wallet_balance': wallet.balance,
        **totals,
    })


@csrf_exempt
def payment_verify(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)

    payment_id = request.POST.get('razorpay_payment_id', '')
    order_id = request.POST.get('razorpay_order_id', '')
    signature = request.POST.get('razorpay_signature', '')

    try:
        import razorpay
        payment_service.confirm_razorpay_payment(payment_id, order_id, signature)
        # Clear session coupon after successful payment
        coupon_service.clear_session_coupon(request)
        return JsonResponse({'status': 'success', 'message': 'Payment successful.'})
    except razorpay.errors.SignatureVerificationError:
        logger.warning("Razorpay signature verification failed for order %s", order_id)
        return JsonResponse({'status': 'error', 'message': 'Payment verification failed.'}, status=400)
    except ValueError as e:
        logger.error("Payment confirmation error: %s", str(e))
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    except Exception:
        logger.exception("Unexpected error in payment_verify for order %s", order_id)
        return JsonResponse({'status': 'error', 'message': 'An error occurred.'}, status=500)


@login_required
def payment_failed(request):
    from orders.models import Order
    order_id = request.GET.get('order_id')
    try:
        order = Order.objects.get(order_id=order_id, user=request.user)
        order.status = 'payment pending'
        order.save(update_fields=['status'])
    except Order.DoesNotExist:
        logger.warning("Payment failed for unknown order %s", order_id)
    messages.error(request, "Payment failed. Please try again.")
    return redirect('cart:cart_checkout')


@login_required
def repay_order(request, order_id):
    from orders.models import Order
    order = get_object_or_404(Order, id=order_id, user=request.user)
    try:
        result = payment_service.process_razorpay_payment(request, order, order.order_total)
        return render(request, result['template'], result['context'])
    except Exception:
        logger.exception("Error initiating repayment for order %s", order_id)
        messages.error(request, "Failed to initiate payment. Please try again.")
        return redirect('userlog:user_orders')


# ─── Address ──────────────────────────────────────────────────────────────────

@login_required
def order_address(request):
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            try:
                address = form.save(commit=False)
                address.account = request.user
                address.save()
                messages.success(request, "Address added successfully.")
                return redirect('cart:cart_checkout')
            except Exception:
                logger.exception("Error saving address for user %s", request.user.id)
                messages.error(request, "Failed to save address.")
    else:
        form = AddressForm()

    addresses = Address.objects.filter(account=request.user)
    return render(request, 'user_log/cart_checkout.html', {
        'addresses': addresses,
        'address_form': form,
    })


@login_required
def delete_order_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, account=request.user)
    if request.method == 'POST':
        address.delete()
        messages.success(request, "Address deleted.")
        return redirect('cart:order_address')
    return render(request, 'user_log/order_address_confirm_delete.html', {'address': address})


@login_required
def set_default_order_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, account=request.user)
    try:
        address.set_as_default()
        messages.success(request, "Default address updated.")
    except Exception:
        logger.exception("Error setting default address %s", address_id)
        messages.error(request, "Failed to update default address.")
    return redirect('cart:order_address')


# ─── Wishlist ─────────────────────────────────────────────────────────────────

@login_required
@require_POST
def toggle_wishlist(request):
    from product_management.models import ProductVariant
    product_variant_id = request.POST.get('product_variant_id', '').strip()

    if not product_variant_id or not product_variant_id.isdigit():
        return JsonResponse({'success': False, 'error': 'Invalid variant.'}, status=400)

    try:
        variant = ProductVariant.objects.get(id=int(product_variant_id))
    except ProductVariant.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Product variant not found.'}, status=404)

    try:
        wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
        item, created = WishlistItem.objects.get_or_create(
            wishlist=wishlist, product_variant=variant
        )
        if not created:
            item.delete()
            return JsonResponse({'success': True, 'message': 'Product removed from wishlist.'})
        return JsonResponse({'success': True, 'message': 'Product added to wishlist.'})
    except Exception:
        logger.exception("Error toggling wishlist for user %s, variant %s", request.user.id, product_variant_id)
        return JsonResponse({'success': False, 'error': 'An error occurred.'}, status=500)


@login_required
def view_wishlist(request):
    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
    wishlist_items = WishlistItem.objects.filter(wishlist=wishlist).select_related(
        'product_variant__product', 'product_variant__color'
    )
    return render(request, 'user_log/wishlist.html', {'wishlist_items': wishlist_items})


@login_required
@require_POST
def remove_from_wishlist(request):
    wishlist_item_id = request.POST.get('wishlist_item_id', '').strip()
    try:
        item = get_object_or_404(WishlistItem, id=wishlist_item_id, wishlist__user=request.user)
        item.delete()
        return JsonResponse({'success': True, 'message': 'Removed from wishlist.'})
    except Exception:
        logger.exception("Error removing wishlist item %s", wishlist_item_id)
        return JsonResponse({'success': False, 'error': 'An error occurred.'}, status=500)


@require_GET
def get_counts(request):
    if not request.user.is_authenticated:
        return JsonResponse({'wishlist_count': 0, 'cart_count': 0})

    try:
        wishlist_count = WishlistItem.objects.filter(wishlist__user=request.user).count()
        cart_count = CartItem.objects.filter(cart__user=request.user).count()
        return JsonResponse({'wishlist_count': wishlist_count, 'cart_count': cart_count})
    except Exception:
        logger.exception("Error fetching counts for user %s", request.user.id)
        return JsonResponse({'wishlist_count': 0, 'cart_count': 0})
