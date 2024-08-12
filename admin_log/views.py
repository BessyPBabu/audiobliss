from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login 
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control ,never_cache
from django.views.decorators.csrf import csrf_protect
from django.http import HttpResponseRedirect
from django.contrib import messages
from user_log.models import Account
from django.conf import settings
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import logging
from orders.models import Order, OrderProduct
from orders.forms import OrderForm, PaymentForm
from user_log.forms import AddressForm




logger = logging.getLogger(__name__)

@csrf_protect
def admin_login(request):
    if request.user.is_authenticated and request.user.is_admin:
        return redirect('adminlog:admin_dashboard')

    if request.method == "POST":
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = authenticate(request, email=email, password=password)

        if user is not None and user.is_admin:
            login(request, user)
            logger.debug("Admin authenticated and logged in.")
            return redirect('adminlog:admin_dashboard')
        else:
            logger.debug("Invalid login attempt.")
            messages.error(request, "Invalid email or password!", extra_tags='login_error')

    return render(request, 'admin_log/admin_login.html')

    
          
   

@login_required(login_url='adminlog:admin_login')
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def admin_dashboard(request):
    if not request.user.is_superuser:
        return redirect('adminlog:admin_login')
    return render(request, 'admin_log/index.html')

@never_cache
def admin_logout(request):
    auth_logout(request)
    if settings.ADMIN_SESSION_KEY in request.session:
        del request.session[settings.ADMIN_SESSION_KEY]
    return redirect('adminlog:admin_login')


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def users_list(request):
    if not request.user.is_superuser:
        return redirect('adminlog:admin_login')

    search_query = request.GET.get('query')
    if search_query:
        user_list = Account.objects.filter(username__icontains=search_query, is_superuser=False).order_by('id')
    else:
        user_list = Account.objects.filter(is_superuser=False).order_by('id')  # Filter out superusers

    paginator = Paginator(user_list, 10)
    page = request.GET.get("page")
    try:
        users = paginator.page(page)
    except PageNotAnInteger:
        users = paginator.page(1)
    except EmptyPage:
        users = paginator.page(paginator.num_pages)

    context = {
        'users': users,
    }

    return render(request, 'admin_log/users_list.html', context)



def block_unblock_user(request, user_id):
    if not request.user.is_superuser:
        return redirect('adminlog:admin_login')

    print("block_unblock_user view called")
    logger.debug("block_unblock_user view called")
    logger.debug("User ID: %s", user_id)

    user = get_object_or_404(Account, id=user_id)
    logger.debug("Before update - User is_active: %s", user.is_active)

    user.is_active = not user.is_active
    user.save()

    logger.debug("After update - User is_active: %s", user.is_active)
    print("User status updated")

    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


def base(request):
    return render(request, 'admin_log/base.html')



def order_list(request):
    if not request.user.is_superuser:
        return redirect('adminlog:admin_login')
    
    orders = Order.objects.order_by('-created_at')
    
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            # You might want to add filtering logic here if needed
            pass
    else:
        form = OrderForm()
    
    paginator = Paginator(orders, 10)
    page = request.GET.get('page')
    
    try:
        orders = paginator.page(page)
    except PageNotAnInteger:
        orders = paginator.page(1)
    except EmptyPage:
        orders = paginator.page(paginator.num_pages)
    
    context = {
        'orders': orders,
        'form': form,
    }
    
    return render(request, 'admin_log/order_details.html', context)




@login_required
def order_details(request, order_id):
    if not request.user.is_superuser:
        return redirect('adminlog:admin_login')
    
    # Fetch the order and related items
    order = get_object_or_404(Order, id=order_id)
    order_items = OrderProduct.objects.filter(order=order)

    # Initialize forms with the current order and payment data
    order_form = OrderForm(instance=order)
    # payment_form = PaymentForm(instance=order.payment)

    if request.method == "POST":
        if 'update_order' in request.POST:
            # Process the OrderForm
            order_form = OrderForm(request.POST, instance=order)
            if order_form.is_valid():
                order_form.save()
                messages.success(request, "Order details updated successfully.")
                return redirect('adminlog:order_list')  # Redirect to the order list page
            else:
                messages.error(request, "Invalid order form submission.")
        
        # elif 'update_payment' in request.POST:
        #     # Process the PaymentForm
        #     payment_form = PaymentForm(request.POST, instance=order.payment)
        #     if payment_form.is_valid():
        #         payment_form.save()
        #         messages.success(request, "Payment information updated successfully.")
        #         return redirect('adminlog:order_list')  # Redirect to the order list page
        #     else:
        #         messages.error(request, "Invalid payment form submission.")

    context = {
        'order': order,
        'order_items': order_items,
        'order_form': order_form,
        # 'payment_form': payment_form,
    }
    
    return render(request, 'admin_log/page_orders_detail.html', context)






from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from orders.models import Order

def cancel_order(request, order_id):
    if not request.user.is_superuser:
        return redirect('adminlog:admin_login')
    
    order = get_object_or_404(Order, id=order_id)
    order.status = 'Cancelled'
    order.save()
    messages.success(request, "Order cancelled successfully")
    
    return redirect('adminlog:order_list')
