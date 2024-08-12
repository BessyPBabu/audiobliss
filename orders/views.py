from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from user_log.forms import AddressForm 
from cart.models import Cart, CartItem
from .models import Order,OrderProduct
from .forms import OrderForm
from product_management.models import ProductVariant
import uuid
from django.db import transaction

# Create your views here.


@login_required
def success(request):
    return render(request, 'user_log/success.html')

@login_required
def invoice(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_products = OrderProduct.objects.filter(order=order)
    
    context = {
        'order': order,
        'order_products': order_products,
    }
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
