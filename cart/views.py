from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import Cart, CartItem
from user_log.models import Address
from user_log.forms import AddressForm
from product_management.models import ProductVariant
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from decimal import Decimal
from django.db import transaction
import uuid
from orders.models import  Order, OrderProduct



# Create your views here.

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
    
    # Update the cart item quantity
    cart_item.quantity += quantity
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
    product_variant = cart_item.product_variant
    product_variant.stock += cart_item.quantity
    product_variant.save()
    cart_item.delete()
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
        cart_items = CartItem.objects.filter(cart=cart).select_related('product_variant')
        
        if not cart_items.exists():
            messages.warning(request, 'Your cart is empty.')
            return redirect('cart:cart_view')
        
        cart_total = sum(item.product_variant.price * item.quantity for item in cart_items)
    except Cart.DoesNotExist:
        messages.error(request, 'Cart not found.')
        return redirect('cart:cart_view')

    addresses = Address.objects.filter(account=request.user)
    
    if not addresses.exists():
        messages.info(request, 'Please add an address before proceeding.')
        return redirect('cart:order_address')

    default_address = addresses.filter(is_default=True).first() or addresses.first()

    if request.method == 'POST':
        address_id = request.POST.get('address')
        
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
                    item.product_variant.stock -= item.quantity
                    item.product_variant.save()

                # Create order object
                order = Order.objects.create(
                    user=request.user,
                    address=address,
                    order_id=str(uuid.uuid4()),
                    order_total=cart_total,
                    is_ordered=True
                )
                
                # Save order products
                order_products = [
                    OrderProduct(
                        order=order,
                        user=request.user,
                        product_variant=item.product_variant,
                        quantity=item.quantity,
                        product_price=item.product_variant.price,
                        ordered=True
                    ) for item in cart_items
                ]
                OrderProduct.objects.bulk_create(order_products)
                
                # Clear the cart after placing the order
                cart_items.delete()
                
                messages.success(request, 'Your order has been placed successfully!')
                return redirect('orders:success')
        except Exception as e:
            print(f"Error during order placement: {e}")
            messages.error(request, 'There was an error processing your order. Please try again.')
    
    context = {
        'cart_items': cart_items,
        'cart_total': cart_total,
        'addresses': addresses,
        'default_address': default_address,
    }
    return render(request, 'user_log/cart_checkout.html', context)

    
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


    
 
@login_required
def wishlist(request):
    return render(request, 'user_log/wishlist.html')


