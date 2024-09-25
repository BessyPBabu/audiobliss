from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import Cart, CartItem
from user_log.models import Address, Wallet , WalletHistory
from user_log.forms import AddressForm
from product_management.models import ProductVariant
from django.views.decorators.http import require_POST ,require_GET
from django.views.decorators.csrf import csrf_protect
from decimal import Decimal
from django.db import transaction
import uuid
from orders.models import  Order, OrderProduct, Payment
import razorpay
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .models import Wishlist, WishlistItem
import razorpay
from django.urls import reverse
from coupon.models import Coupon
from coupon.forms import UserCouponForm
from cart.models import Cart
from decimal import Decimal, ROUND_HALF_UP


import logging
logger = logging.getLogger(__name__)


# Create your views here.


#====================================== CART BEGIN ======================================================#


@login_required
def view_cart(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all()
    
    total = sum(item.subtotal for item in cart_items)
    return render(request, 'user_log/cart.html', {'cart_items': cart_items, 'total': total})


@login_required
@require_POST
@csrf_protect
def add_to_cart(request):
    # Retrieve product_variant_id from the POST request
    product_variant_id = request.POST.get('product_variant_id')
    
    # Check if the product_variant_id is valid
    if not product_variant_id or not product_variant_id.isdigit():
        return JsonResponse({'error': 'Invalid product variant ID'}, status=400)
    
    # Get the ProductVariant object or return 404 if not found
    product_variant = get_object_or_404(ProductVariant, id=int(product_variant_id))
    
    # Retrieve or create a Cart object for the current user
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    # Retrieve and validate the quantity from the POST request
    try:
        quantity = int(request.POST.get('quantity', 1))
    except ValueError:
        return JsonResponse({'error': 'Invalid quantity'}, status=400)
    
    if quantity <= 0:
        return JsonResponse({'error': 'Quantity must be greater than zero'}, status=400)
    
    # Check stock availability
    if product_variant.stock < quantity:
        return JsonResponse({'error': 'Not enough stock'}, status=400)
    
    # Retrieve or create a CartItem object for the given cart and product variant
    cart_item, item_created = CartItem.objects.get_or_create(
        cart=cart,
        product_variant=product_variant,
        defaults={'quantity': 0}
    )
    
    # Check maximum quantity per user
    if cart_item.quantity + quantity > product_variant.max_quantity_per_user:
        return JsonResponse({'error': 'Maximum quantity per user exceeded'}, status=400)
    
    # Calculate the discounted price
    product = product_variant.product
    best_offer = product.get_best_offer()
    if best_offer:
        discounted_price = best_offer.apply_discount(product_variant.price)
    else:
        discounted_price = product_variant.price
    
    # Update the cart item quantity
    cart_item.quantity += quantity
    cart_item.price_at_addition = discounted_price
    cart_item.save()
    
    # Calculate the total price for the cart
    cart_total = Decimal(sum(item.subtotal for item in cart.items.all()))

    
    return JsonResponse({
        'success': True,
        'cart_total': str(cart_total),
        'item_count': cart.items.count()
    })
        

@login_required
def remove_from_cart(request, cart_item_id):
    cart_item = get_object_or_404(CartItem, id=cart_item_id, cart__user=request.user)

    # Capture the cart total before deleting the item
    cart = cart_item.cart
    cart_item.delete()

    # Recalculate the cart total after deletion
    cart_total = sum(item.subtotal for item in cart.items.all())
    cart_count = cart.items.count()

    # Return JSON response if request is AJAX, otherwise redirect
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'cart_total': cart_total,
            'cart_count': cart_count,
            'message': f"{cart_item.product_variant} removed from your cart."
        })
    else:
        messages.success(request, f"{cart_item.product_variant} removed from your cart.")
        return redirect('cart:view_cart')


@login_required
def update_cart(request, cart_item_id):
    if request.method == 'POST':
        cart_item = get_object_or_404(CartItem, id=cart_item_id, cart__user=request.user)
        product_variant = cart_item.product_variant

        try:
            new_quantity = int(request.POST.get('quantity', 1))
        except ValueError:
            return JsonResponse({'error': 'Invalid quantity'}, status=400)

        if new_quantity <= 0:
            # Remove item if quantity is 0 or negative
            product_variant.stock += cart_item.quantity
            product_variant.save()
            cart_item.delete()
        elif new_quantity > product_variant.max_quantity_per_user:
            return JsonResponse({'error': 'Maximum quantity per user exceeded'}, status=400)
        elif product_variant.stock + cart_item.quantity >= new_quantity:
            stock_change = new_quantity - cart_item.quantity
            product_variant.stock -= stock_change
            product_variant.save()
            cart_item.quantity = new_quantity
            cart_item.save()
        else:
            return JsonResponse({'error': 'Not enough stock'}, status=400)

        # Recalculate cart totals
        cart = request.user.cart
        cart_items = cart.items.all()
        cart_total = sum(item.subtotal for item in cart_items)
        cart_count = sum(item.quantity for item in cart_items)

        item_subtotal = cart_item.quantity * cart_item.product_variant.price

        return JsonResponse({
            'success': True,
            'item_subtotal': item_subtotal,
            'cart_total': cart_total,
            'cart_count': cart_count,
            'message': 'Cart updated successfully.'
        })

    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def clear_cart(request):
    if request.method == 'POST':
        cart = Cart.objects.get(user=request.user)
        cart_items = cart.items.all()
        for item in cart_items:
            item.product_variant.stock += item.quantity
            item.product_variant.save()
        cart_items.delete()
        messages.success(request, "Your cart has been cleared.")
    return redirect('cart:view_cart')


@login_required
def cart_checkout(request):
    try:
        cart = Cart.objects.get(user=request.user)
        cart_items = cart.items.select_related('product_variant')
        
        if not cart_items.exists():
            messages.warning(request, 'Your cart is empty.')
            return redirect('cart:cart_view')
        
        # # Calculate prices and total
        cart_total = sum(item.subtotal for item in cart.items.all()).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
    except Cart.DoesNotExist:
        messages.error(request, 'Cart not found.')
        return redirect('cart:cart_view')

    # Get or create user's wallet
    wallet, created = Wallet.objects.get_or_create(user=request.user)
    addresses = Address.objects.filter(account=request.user)
    
    if not addresses.exists():
        messages.info(request, 'Please add an address before proceeding.')
        return redirect('cart:order_address')

    default_address = addresses.filter(is_default=True).first() or addresses.first()

    # Check if a coupon is applied
    discount_amount = Decimal('0.00')

    # Check if a coupon is applied (stored in session)
    if 'coupon' in request.session:
        coupon_data = request.session['coupon']
        print(f"Coupon Data from Session: {coupon_data}")
        
        # Check if cart total has changed
        if Decimal(coupon_data['cart_total_at_application']) != cart_total:
            # Recalculate discount if cart total changed
            if coupon_data['discount_type'] == 'percentage':
                discount_amount = (cart_total * Decimal(coupon_data['discount_value']) / Decimal(100)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            else:  # 'FIXED' discount type
                discount_amount = min(Decimal(coupon_data['discount_value']), cart_total).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        else:
            # Use stored discount amount if cart total hasn't changed
            discount_amount = Decimal(coupon_data['discount_amount'])
        
        print(f"Applied Discount Amount: {discount_amount}")
    
    # Calculate the final total after applying the discount
    final_total = (cart_total - discount_amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    print(f"Cart Total: {cart_total}")
    print(f"Discount Amount: {discount_amount}")
    print(f"Final Total: {final_total}")

    service_charge = Decimal('65')
    final_total_with_service_charge = (final_total + service_charge).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    print(f"Final Total with Service Charge: {final_total_with_service_charge}")

    razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    if request.method == 'POST':
        address_id = request.POST.get('address')
        payment_method = request.POST.get('payment_option')
        
        if not address_id:
            messages.error(request, 'Please select an address.')
            return redirect('cart:cart_checkout')
        
        try:
            with transaction.atomic():
                address = get_object_or_404(Address, id=address_id, account=request.user)
                
                # Check if products are still available and update inventory
                for item in cart_items:
                    if item.quantity > item.product_variant.stock:
                        messages.error(request, f'{item.product_variant.product.title} is out of stock.')
                        return redirect('cart:cart_checkout')

                # Create pending order object
                order = Order.objects.create(
                    user=request.user,
                    address=address,
                    order_id=str(uuid.uuid4()),
                    order_total=final_total_with_service_charge,
                    tax=0,  # You may want to calculate tax here
                    ip=request.META.get('REMOTE_ADDR'),
                    is_ordered=False,
                    
                )

                # Save order products
                for item in cart_items:
                    OrderProduct.objects.create(
                        order=order,
                        user=request.user,
                        product_variant=item.product_variant,
                        quantity=item.quantity,
                        product_price=item.product_variant.price,
                        ordered=False
                    )

                print(f"Order created with ID: {order.id}")

                if payment_method == 'Wallet':
                    return process_wallet_payment(request, order, wallet, final_total_with_service_charge, cart_items)
                elif payment_method == 'Razorpay':
                    return process_razorpay_payment(request, order, final_total_with_service_charge, razorpay_client)
                else:
                    return process_cod_payment(request, order, final_total_with_service_charge, cart_items)


                # if payment_method == 'Wallet':
                #     if wallet.balance >= final_total_with_service_charge:
                #         # Full payment from wallet
                #         wallet.balance -= final_total_with_service_charge
                #         wallet.save()
                #         # Record the wallet transaction
                #         WalletHistory.objects.create(
                #             wallet=wallet,
                #             type='Wallet Payment',
                #             amount=final_total_with_service_charge
                #         )
                #         payment = Payment.objects.create(
                #             user=request.user,
                #             payment_id=f'WALLET_{order.order_id}',
                #             payment_method='Wallet',
                #             amount_paid=final_total_with_service_charge,
                #             status="Completed"
                #         )
                #         order.is_ordered = True
                #         order.payment = payment
                #         order.save()
                #         OrderProduct.objects.filter(order=order).update(ordered=True)
                #         cart_items.delete()
                #         messages.success(request, 'Your order has been placed successfully using your wallet balance!')
                #         return redirect('orders:success')
                #     else:
                #         # Partial payment from wallet, remaining from Razorpay
                #         amount_from_wallet = wallet.balance
                #         amount_from_razorpay = final_total_with_service_charge - amount_from_wallet
                #         wallet.balance = Decimal('0')
                #         wallet.save()

                #         # Record the wallet transaction
                #         WalletHistory.objects.create(
                #             wallet=wallet,
                #             type='Wallet Payment',
                #             amount=amount_from_wallet
                #         )

                        
                #         # Create Razorpay order for remaining amount
                #         razorpay_order = razorpay_client.order.create(dict(amount=int(amount_from_razorpay * 100), currency='INR', payment_capture='0'))
                #         order.razorpay_order_id = razorpay_order['id']
                #         order.save()

                #         context = {
                #             'order': order,
                #             'razorpay_order_id': razorpay_order['id'],
                #             'razorpay_merchant_key': settings.RAZORPAY_KEY_ID,
                #             'razorpay_amount': int(amount_from_razorpay * 100),
                #             'currency': 'INR',
                #             'callback_url': request.build_absolute_uri(reverse('cart:payment_verify')),
                #             'amount_from_wallet': amount_from_wallet,
                #         }
                #         return render(request, 'user_log/razorpay_payment.html', context)

                # elif payment_method == 'Razorpay':
                #     # Razorpay order creation
                #     razorpay_order = razorpay_client.order.create(dict(amount=int(final_total_with_service_charge * 100), currency='INR', payment_capture='0'))
                #     order.razorpay_order_id = razorpay_order['id']
                #     order.save()

                #     context = {
                #         'order': order,
                #         'razorpay_order_id': razorpay_order['id'],
                #         'razorpay_merchant_key': settings.RAZORPAY_KEY_ID,
                #         'razorpay_amount': int(final_total_with_service_charge * 100),
                #         'currency': 'INR',
                #         'callback_url': request.build_absolute_uri(reverse('cart:payment_verify'))
                #     }
                #     return render(request, 'user_log/razorpay_payment.html', context)
                # else:
                #     # If COD or other payment option
                #     payment = Payment.objects.create(
                #         user=request.user,
                #         payment_id=f'COD_{order.order_id}',
                #         payment_method='Cash On Delivery',
                #         amount_paid=final_total_with_service_charge,
                #         status="Pending"
                #     )
                #     order.is_ordered = True
                #     order.payment = payment
                #     order.save()
                #     OrderProduct.objects.filter(order=order).update(ordered=True)
                #     cart_items.delete()
                #     messages.success(request, 'Your order has been placed successfully!')
                #     return redirect('orders:success')
        except Exception as e:
            print(f"Error during order placement: {e}")
            messages.error(request, 'There was an error processing your order. Please try again.')
    

    # Fetch active coupons for display in the template
    active_coupons = Coupon.objects.filter(active=True)


    context = {
        'cart': cart,
        'cart_items': cart_items,
        'cart_total': cart_total,
        'final_total': final_total,
        'discount_amount': discount_amount,
        'addresses': addresses,
        'default_address': default_address,
        'active_coupons': active_coupons,
        'coupon_form': UserCouponForm(),
        'wallet_balance': wallet.balance,
        'service_charge': service_charge,
        'final_total_with_service_charge': final_total_with_service_charge,

    }
    
    return render(request, 'user_log/cart_checkout.html', context)

def process_wallet_payment(request, order, wallet, total_amount, cart_items):
    if wallet.balance >= total_amount:
        wallet.balance -= total_amount
        wallet.save()
        WalletHistory.objects.create(
            wallet=wallet,
            type='Wallet Payment',
            amount=total_amount
        )
        payment = Payment.objects.create(
            user=request.user,
            payment_id=f'WALLET_{order.order_id}',
            payment_method='Wallet',
            amount_paid=total_amount,
            status="Completed"
        )
        order.is_ordered = True
        order.payment = payment
        order.save()
        OrderProduct.objects.filter(order=order).update(ordered=True)
        cart_items.delete()
        messages.success(request, 'Your order has been placed successfully using your wallet balance!')
        return redirect('orders:success')
    else:
        amount_from_wallet = wallet.balance
        amount_from_razorpay = total_amount - amount_from_wallet
        wallet.balance = Decimal('0')
        wallet.save()

        WalletHistory.objects.create(
            wallet=wallet,
            type='Wallet Payment',
            amount=amount_from_wallet
        )

        razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        razorpay_order = razorpay_client.order.create(dict(amount=int(amount_from_razorpay * 100), currency='INR', payment_capture='0'))
        order.razorpay_order_id = razorpay_order['id']
        order.save()

        context = {
            'order': order,
            'razorpay_order_id': razorpay_order['id'],
            'razorpay_merchant_key': settings.RAZORPAY_KEY_ID,
            'razorpay_amount': int(amount_from_razorpay * 100),
            'currency': 'INR',
            'callback_url': request.build_absolute_uri(reverse('cart:payment_verify')),
            'amount_from_wallet': amount_from_wallet,
        }
        return render(request, 'user_log/razorpay_payment.html', context)

def process_razorpay_payment(request, order, total_amount, razorpay_client):
    razorpay_order = razorpay_client.order.create(dict(amount=int(total_amount * 100), currency='INR', payment_capture='0'))
    order.razorpay_order_id = razorpay_order['id']
    order.save()

    context = {
        'order': order,
        'razorpay_order_id': razorpay_order['id'],
        'razorpay_merchant_key': settings.RAZORPAY_KEY_ID,
        'razorpay_amount': int(total_amount * 100),
        'currency': 'INR',
        'callback_url': request.build_absolute_uri(reverse('cart:payment_verify'))
    }
    return render(request, 'user_log/razorpay_payment.html', context)

def process_cod_payment(request, order, total_amount, cart_items):
    payment = Payment.objects.create(
        user=request.user,
        payment_id=f'COD_{order.order_id}',
        payment_method='Cash On Delivery',
        amount_paid=total_amount,
        status="Pending"
    )
    order.is_ordered = True
    order.payment = payment
    order.save()
    OrderProduct.objects.filter(order=order).update(ordered=True)
    cart_items.delete()
    messages.success(request, 'Your order has been placed successfully!')
    return redirect('orders:success')


@csrf_exempt
@transaction.atomic
def payment_verify(request):
    if request.method == "POST":
        razorpay_payment_id = request.POST.get('razorpay_payment_id', '')
        razorpay_order_id = request.POST.get('razorpay_order_id', '')
        razorpay_signature = request.POST.get('razorpay_signature', '')
        
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        
        try:
            # Verify the payment signature
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            }
            client.utility.verify_payment_signature(params_dict)
            
            # Signature verification successful, process the order
            order = Order.objects.select_for_update().get(razorpay_order_id=razorpay_order_id)
            
            if order.is_ordered:
                # Order already processed
                return JsonResponse({'status': 'success', 'message': 'Order already processed'})
            
            user = order.user  # Get the user from the order

            # Get the Razorpay payment details
            razorpay_payment = client.payment.fetch(razorpay_payment_id)
            razorpay_amount = Decimal(razorpay_payment['amount']) / 100  # Convert from paise to rupees

            # Calculate the amount paid from wallet (if any)
            amount_from_wallet = order.order_total - razorpay_amount

            if amount_from_wallet > 0:
                # Create a wallet payment record
                wallet_payment = Payment.objects.create(
                    user=user,
                    payment_id=f'WALLET_{order.order_id}',
                    payment_method="Wallet",
                    amount_paid=amount_from_wallet,
                    status="Completed"
                )

            # Create the Razorpay payment record
            razorpay_payment = Payment.objects.create(
                user=user,
                payment_id=razorpay_payment_id,
                payment_method="Razorpay",
                amount_paid=razorpay_amount,
                status="Completed"
            )

            order.is_ordered = True
            order.payment = razorpay_payment  # We're setting the main payment as Razorpay
            order.payment_status = "Completed"
            order.status = "Confirmed"
            order.save()
            
            # Update ordered status for order products and reduce stock
            for order_product in OrderProduct.objects.filter(order=order):
                order_product.ordered = True
                order_product.save()
                
                product_variant = order_product.product_variant
                product_variant.stock -= order_product.quantity
                product_variant.save()
            
            # Clear the cart
            Cart.objects.filter(user=user).delete()
            
            return JsonResponse({'status': 'success', 'message': 'Payment successful and order placed'})
        
        except razorpay.errors.SignatureVerificationError:
            return JsonResponse({'status': 'error', 'message': 'Payment verification failed'})
        except Order.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Order not found'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

    #         wallet = Wallet.objects.get(user=user)
            
    #         # Check if partial payment was made from wallet
    #         amount_from_wallet = Decimal('0')
    #         if wallet.balance < order.order_total:
    #             amount_from_wallet = wallet.balance
    #             wallet.balance = Decimal('0')
    #             wallet.save()

    #             # Record the wallet transaction
    #             WalletHistory.objects.create(
    #                 wallet=wallet,
    #                 type='Wallet Payment',
    #                 amount=amount_from_wallet
    #             )
            
    #         razorpay_amount = order.order_total - amount_from_wallet
            
    #         razorpay_payment = Payment.objects.create(
    #             user=user,
    #             payment_id=razorpay_payment_id,
    #             payment_method="Razorpay",
    #             amount_paid=razorpay_amount,
    #             status="Completed"
    #         )

    #         # If wallet was used, create a separate payment record for it
    #         if amount_from_wallet > 0:
    #             wallet_payment = Payment.objects.create(
    #                 user=user,
    #                 payment_id=f'WALLET_{order.order_id}',
    #                 payment_method="Wallet",
    #                 amount_paid=amount_from_wallet,
    #                 status="Completed"
    #             )

            
    #         order.is_ordered = True
    #         order.payment = razorpay_payment
    #         order.payment_status = "Completed"
    #         order.status = "Confirmed"
    #         order.save()
            
    #         # Update ordered status for order products and reduce stock
    #         for order_product in OrderProduct.objects.filter(order=order):
    #             order_product.ordered = True
    #             order_product.save()
                
    #             product_variant = order_product.product_variant
    #             product_variant.stock -= order_product.quantity
    #             product_variant.save()
            
    #         # Clear the cart
    #         Cart.objects.filter(user=user).delete()
            
    #         return JsonResponse({'status': 'success', 'message': 'Payment successful and order placed'})
        
    #     except razorpay.errors.SignatureVerificationError:
    #         return JsonResponse({'status': 'error', 'message': 'Payment verification failed'})
    #     except Order.DoesNotExist:
    #         return JsonResponse({'status': 'error', 'message': 'Order not found'})
    #     except Exception as e:
    #         return JsonResponse({'status': 'error', 'message': str(e)})
    
    # return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


@login_required
def payment_failed(request):
    order_id = request.GET.get('order_id')
    try:
        order = Order.objects.get(order_id=order_id, user=request.user)
        order.status = "Payment Pending"
        order.save()
        messages.error(request, 'Your payment has failed. Please try again or choose a different payment method.')
        return redirect('cart:cart_checkout')
    except Order.DoesNotExist:
        messages.error(request, 'Order not found.')
        return redirect('cart:view_cart')
    

@login_required
def repay_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Initialize Razorpay client
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    # Create a new Razorpay order
    razorpay_order = client.order.create({
        'amount': int(order.order_total * 100),  # Amount in paise
        'currency': 'INR',
        'payment_capture': '0'  # Manual capture
    })

    # Update the order with new Razorpay order ID
    order.razorpay_order_id = razorpay_order['id']
    order.save()

    # Prepare context for the template
    context = {
        'order': order,
        'razorpay_order_id': razorpay_order['id'],
        'razorpay_merchant_key': settings.RAZORPAY_KEY_ID,
        'razorpay_amount': int(order.order_total * 100),
        'currency': 'INR',
        'callback_url': request.build_absolute_uri(reverse('cart:payment_verify'))
    }

    return render(request, 'user_log/razorpay_payment.html', context)

 #====================================== CART ENDS ======================================================#
    

#====================================== ORDER ADDRESS BEGIN ======================================================#


@login_required
def order_address(request):
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.account = request.user
            address.save()
            messages.success(request, 'Address added successfully.')
            return redirect('cart:cart_checkout')
    else:
        form = AddressForm()
    
    addresses = Address.objects.filter(account=request.user)
    context = {
        'addresses': addresses,
        'address_form': form,
    }
    return render(request, 'user_log/cart_checkout.html', context)


@login_required
def delete_order_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, account=request.user)
    if request.method == 'POST':
        address.delete()
        messages.success(request, 'Address deleted successfully.')
        return redirect('cart:order_address')
    return render(request, 'user_log/confirm_delete.html', {'address': address})

@login_required
def set_default_order_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, account=request.user)
    Address.objects.filter(account=request.user).update(is_default=False)
    address.is_default = True
    address.save()
    messages.success(request, 'Default address set successfully.')
    return redirect('cart:order_address')

#====================================== ORDER ADDRESS ENDS ======================================================#
    

#====================================== WISHLIST BEGINS ======================================================#
 
@login_required
@require_POST
def add_to_wishlist(request):
    product_variant_id = request.POST.get('product_variant_id')
    
    try:
        product_variant = ProductVariant.objects.get(id=product_variant_id)
        
        # Get or create a wishlist for the user
        wishlist, created = Wishlist.objects.get_or_create(user=request.user)
        
        # Check if the product variant is already in the wishlist
        wishlist_item, created = WishlistItem.objects.get_or_create(
            wishlist=wishlist,
            product_variant=product_variant
        )
        
        if created:
            return JsonResponse({'success': True, 'message': 'Added to wishlist'})
        else:
            return JsonResponse({'success': False, 'message': 'Item already in wishlist'})

    except ProductVariant.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Product variant not found'})

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})
    

@login_required
def view_wishlist(request):
    wishlist, created = Wishlist.objects.get_or_create(user=request.user)
    wishlist_items = WishlistItem.objects.filter(wishlist=wishlist)
    
    # Debugging output
    print(f"Wishlist for {request.user}: {wishlist_items}")

    return render(request, 'user_log/wishlist.html', {'wishlist_items': wishlist_items})

    
@login_required
@require_POST
def remove_from_wishlist(request):
    print("Remove from wishlist view called")
    wishlist_item_id = request.POST.get('wishlist_item_id')
    print(f"Wishlist item ID: {wishlist_item_id}")

    try:
        wishlist_item = get_object_or_404(WishlistItem, id=wishlist_item_id, wishlist__user=request.user)
        wishlist_item.delete()
        return JsonResponse({'success': True, 'message': 'Removed from wishlist'})
    except WishlistItem.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Item not found in wishlist'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


def get_counts(request):
    if request.user.is_authenticated:
        wishlist_count = WishlistItem.objects.filter(wishlist__user=request.user).count()
        cart_count = CartItem.objects.filter(cart__user=request.user).count()
    else:
        wishlist_count = 0
        cart_count = 0
    
    return JsonResponse({
        'wishlist_count': wishlist_count,
        'cart_count': cart_count
    })


@login_required
@require_POST
def toggle_wishlist(request):
    product_variant_id = request.POST.get('product_variant_id')

    # Fetch the product variant instance using the ID
    try:
        product_variant = ProductVariant.objects.get(id=product_variant_id)
    except ProductVariant.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Product variant not found.'})

    # Get the user's wishlist or create it if it doesn't exist
    wishlist, created = Wishlist.objects.get_or_create(user=request.user)

    # Check if the item is already in the wishlist
    wishlist_item, item_created = WishlistItem.objects.get_or_create(
        wishlist=wishlist,
        product_variant=product_variant
    )
    
    if not item_created:
        # If the item already exists, remove it from the wishlist
        wishlist_item.delete()
        return JsonResponse({'success': True, 'message': 'Product removed from wishlist.'})
    else:
        # If the item is newly created, it's added to the wishlist
        return JsonResponse({'success': True, 'message': 'Product added to wishlist.'})


@login_required
@require_GET
def check_wishlist(request):
    product_variant_id = request.GET.get('product_variant_id')
    user = request.user
    
    in_wishlist = Wishlist.objects.filter(user=user, product_variant_id=product_variant_id).exists()
    
    return JsonResponse({'in_wishlist': in_wishlist})

#====================================== WISHLIST ENDS ======================================================#