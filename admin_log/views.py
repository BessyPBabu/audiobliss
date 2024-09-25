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
from orders.models import Order, OrderProduct, Payment, ReturnRequest
from orders.forms import OrderForm
from user_log.forms import AddressForm
import razorpay
from django.conf import settings
from orders.models import Order
from user_log.models import Wallet, WalletHistory
from django.utils import timezone
from datetime import datetime
from django.db.models import Sum, Count
from datetime import timedelta
from product_management.models import Product
from coupon.models import CouponUsage
from django.db import transaction


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
    revenue = Order.objects.filter(is_ordered=True).aggregate(Sum('order_total'))['order_total__sum'] or 0

    # Get orders count
    orders_count = Order.objects.filter(is_ordered=True).count()

    # Get product count
    product_count = Product.objects.count()

    # Get total users count
    total_users_count = Account.objects.count()

    # Get last 5 orders
    last_orders = Order.objects.filter(is_ordered=True).order_by('-created_at')[:5]

    # Daily sales report data
    today = timezone.now().date()
    last_week = today - timedelta(days=6)
    daily_orders = Order.objects.filter(created_at__date__range=[last_week, today], is_ordered=True)
    daily_data = daily_orders.values('created_at__date').annotate(count=Count('id')).order_by('created_at__date')
    dates = [item['created_at__date'].strftime('%Y-%m-%d') for item in daily_data]
    counts = [item['count'] for item in daily_data]

    # Monthly sales report data
    last_month = today - timedelta(days=30)
    monthly_orders = Order.objects.filter(created_at__date__range=[last_month, today], is_ordered=True)
    monthly_data = monthly_orders.values('created_at__date').annotate(count=Count('id')).order_by('created_at__date')
    monthly_dates = [item['created_at__date'].strftime('%Y-%m-%d') for item in monthly_data]
    monthly_counts = [item['count'] for item in monthly_data]

    # Yearly sales report data
    last_year = today - timedelta(days=365)
    yearly_orders = Order.objects.filter(created_at__date__range=[last_year, today], is_ordered=True)
    yearly_data = yearly_orders.values('created_at__month').annotate(count=Count('id')).order_by('created_at__month')
    yearly_dates = [timezone.datetime(2023, item['created_at__month'], 1).strftime('%B') for item in yearly_data]
    yearly_counts = [item['count'] for item in yearly_data]

    # Order status data
    order_status_data = Order.objects.values('status').annotate(count=Count('id'))
    status_labels = [item['status'] for item in order_status_data]
    order_counts = [item['count'] for item in order_status_data]

    # New code for best-selling products, categories, and brands
    best_selling_products = OrderProduct.objects.values('product_variant__product__title') \
        .annotate(total_quantity=Sum('quantity')) \
        .order_by('-total_quantity')[:5]

    best_selling_categories = OrderProduct.objects.values('product_variant__product__category__name') \
        .annotate(total_quantity=Sum('quantity')) \
        .order_by('-total_quantity')[:5]

    best_selling_brands = OrderProduct.objects.values('product_variant__product__brand__name') \
        .annotate(total_quantity=Sum('quantity')) \
        .order_by('-total_quantity')[:5]


    context = {
        'revenue': revenue,
        'orders_count': orders_count,
        'product_count': product_count,
        'total_users_count': total_users_count,
        'last_orders': last_orders,
        'dates': dates,
        'counts': counts,
        'monthlyDates': monthly_dates,
        'monthlyCounts': monthly_counts,
        'yearlyDates': yearly_dates,
        'yearlyCounts': yearly_counts,
        'statusLabels': status_labels,
        'orderCounts': order_counts,
        'best_selling_products': best_selling_products,
        'best_selling_categories': best_selling_categories,
        'best_selling_brands': best_selling_brands,
    }

    return render(request, 'admin_log/index.html',context)

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
    
    orders = Order.objects.filter(is_ordered=True).order_by('-created_at')
    
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
    payment = get_object_or_404(Payment, order=order)
    order_items = OrderProduct.objects.filter(order=order)

    # Initialize forms with the current order and payment data
    order_form = OrderForm(instance=order)

    if request.method == "POST":
        if 'update_order' in request.POST:
            # Process the OrderForm
            order_form = OrderForm(request.POST, instance=order)
            if order_form.is_valid():
                updated_order = order_form.save()
                messages.success(request, "Order details updated successfully.")
                
                # If the order is cancelled and paid with Razorpay, simulate the refund
                if updated_order.status == 'Cancelled' and not updated_order.is_refunded:
                    print("Simulating refund process...")
                    try:
                        process_cancellation_refund(updated_order)
                        messages.success(request, "Order cancelled and refund processed successfully.")
                    except Exception as e:
                        messages.error(request, f"Error processing refund: {str(e)}")
                
                return redirect('adminlog:order_list')
            else:
                messages.error(request, "Invalid order form submission.")

        elif 'approve_return' in request.POST:
            # Handle return request approval
            return_request_id = request.POST.get('return_request_id')
            return_request = get_object_or_404(ReturnRequest, id=return_request_id)

            try:
                process_return_request_approval(return_request)
                messages.success(request, f"Return request #{return_request_id} approved, refund credited to the wallet, and order status updated to 'Returned'.")
            except Exception as e:
                messages.error(request, f"An error occurred while processing the return request: {str(e)}")
            return redirect('adminlog:order_list')

        elif 'reject_return' in request.POST:
            # Handle return request rejection
            return_request_id = request.POST.get('return_request_id')
            return_request = get_object_or_404(ReturnRequest, id=return_request_id)
            return_request.status = 'Rejected'
            return_request.save()
            messages.success(request, f"Return request #{return_request_id} has been rejected.")

    # Fetch pending return requests for this order
    pending_requests = ReturnRequest.objects.filter(order=order, status='Pending')

    context = {
        'order': order,
        'order_items': order_items,
        'order_form': order_form,
        'pending_requests': pending_requests,
    }
    
    return render(request, 'admin_log/page_orders_detail.html', context)



def process_cancellation_refund(order):
    with transaction.atomic():
        payment = get_object_or_404(Payment, order=order)
        if payment.payment_method in ['Razorpay', 'Wallet']:
            wallet, created = Wallet.objects.get_or_create(user=order.user)
            wallet.balance += order.total_amount
            wallet.save()
            
            WalletHistory.objects.create(
                wallet=wallet,
                amount=order.total_amount,
                type='Refund'
            )
            
            order.is_refunded = True
            order.save()

def process_return_request_approval(return_request):
    with transaction.atomic():
        return_request.status = 'Approved'
        return_request.refunded = True     

        order = return_request.order
        wallet, created = Wallet.objects.get_or_create(user=order.user)
        refund_amount = order.order_total  # You may adjust this based on your refund policy
        wallet.balance += refund_amount
        wallet.save()

        WalletHistory.objects.create(
            wallet=wallet,
            amount=refund_amount,
            type='Refund'
        )

        order.status = 'Returned'
        order.is_refunded = True
        order.save()

        return_request.save()
                    
            #         # Simulate refund: Credit the amount to the user's wallet
            #         wallet, created = Wallet.objects.get_or_create(user=updated_order.user)
            #         wallet.balance += updated_order.total_amount
            #         wallet.save()
            #         print(f"Wallet after simulated refund: {wallet.balance}")
                    
            #         # Log the transaction in WalletHistory
            #         WalletHistory.objects.create(
            #             wallet=wallet,
            #             amount=updated_order.total_amount,
            #             type='Refund'  # or 'Credited'
            #         )
                    
            #         # Mark order as refunded
            #         updated_order.is_refunded = True
            #         updated_order.save()
                    
            #         messages.success(request, "Order cancelled and refund processed successfully (simulated).")
            #     return redirect('adminlog:order_list')  # Redirect to the order list page
            # else:
            #     messages.error(request, "Invalid order form submission.")

        # Handle return request approval
    #     if 'approve_return' in request.POST:
    #         return_request_id = request.POST.get('return_request_id')
    #         return_request = get_object_or_404(ReturnRequest, id=return_request_id)

    #         try:
    #             with transaction.atomic():
    #                 # Approve the return request
    #                 return_request.status = 'Approved'
    #                 return_request.save()

    #                 # Process wallet refund transaction
    #                 wallet, created = Wallet.objects.get_or_create(user=return_request.order.user)
    #                 refund_amount = return_request.order.order_total  # You can adjust this based on specific refund logic
    #                 wallet.balance += refund_amount
    #                 wallet.save()

    #                 # Log the refund in WalletHistory
    #                 WalletHistory.objects.create(
    #                     wallet=wallet,
    #                     amount=refund_amount,
    #                     type='Refund'  # Mark as refund
    #                 )

    #                 # Update the order status to 'Returned'
    #                 return_request.order.status = 'Returned'
    #                 return_request.order.save()

    #                 messages.success(request, f"Return request #{return_request_id} approved, refund credited to the wallet, and order status updated to 'Returned'.")
    #         except Exception as e:
    #             messages.error(request, f"An error occurred while processing the refund: {e}")
    #         return redirect('adminlog:order_list')

    #     # Handle return request rejection
    #     elif 'reject_return' in request.POST:
    #         return_request_id = request.POST.get('return_request_id')
    #         return_request = get_object_or_404(ReturnRequest, id=return_request_id)
    #         return_request.status = 'Rejected'
    #         return_request.save()

    #         messages.success(request, f"Return request #{return_request_id} has been rejected.")

    # # Fetch pending return requests for this specific order
    # pending_requests = ReturnRequest.objects.filter(order=order, status='Pending')


    # context = {
    #     'order': order,
    #     'order_items': order_items,
    #     'order_form': order_form,
    #     'pending_requests': pending_requests,
    # }
    
    # return render(request, 'admin_log/page_orders_detail.html', context)


@login_required
def sales_report(request):
    # Get the report type from GET request
    report_type = request.GET.get('report_type', '30days')  # Default to last 30 days if no report type is provided

    # Get start_date and end_date based on report_type
    if report_type == 'custom':
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        if start_date and end_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        else:
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=30)
    elif report_type == 'daily':
        start_date = end_date = timezone.now().date()
    elif report_type == 'weekly':
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=7)
    elif report_type == 'monthly':
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
    elif report_type == 'yearly':
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=365)
    else:  # Default to last 30 days
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)

    # Filter orders
    orders = Order.objects.filter(
        created_at__date__range=[start_date, end_date],
        is_ordered=True
    ).exclude(payment__isnull=True).order_by('-created_at')

    # Calculate overall metrics
    total_sales_count = orders.count()
    total_order_amount = sum(order.order_total for order in orders)
    total_discount_amount = sum(
        sum(usage.discount_amount for usage in CouponUsage.objects.filter(order=order))
        for order in orders
    )

    # Set up pagination
    paginator = Paginator(orders, 10)  # Show 10 orders per page
    page_number = request.GET.get('page')  # Get the current page number from the GET request
    page_obj = paginator.get_page(page_number)

    # Prepare order data including coupon information for the current page
    order_data = []
    for order in page_obj:
        coupon_usages = CouponUsage.objects.filter(order=order)
        # Debugging: Check if coupon usages are being fetched
        print(f"Order ID: {order.id}, Coupon Usages: {coupon_usages}")

        coupon_info = "No coupon applied"
        
        if coupon_usages.exists():
            coupon_info = ", ".join([f"{usage.code} (₹{usage.discount_amount})" for usage in coupon_usages])

        # Fetch order items
        order_items = OrderProduct.objects.filter(order=order)
        item_details = [
            f"{item.product_variant.product.title} (x{item.quantity}) - ₹{item.product_price}" for item in order_items
        ]
        item_details_str = "<br>".join(item_details)
        



        order_data.append({
            'order': order,
            'coupon_info': coupon_info,
            'item_details': item_details_str

        })

    context = {
        'order_data': order_data,
        'page_obj': page_obj,
        'start_date_value': start_date.strftime('%Y-%m-%d'),
        'end_date_value': end_date.strftime('%Y-%m-%d'),
        'total_sales_count': total_sales_count,  # Overall sales count
        'total_order_amount': total_order_amount,  # Overall order amount
        'total_discount_amount': total_discount_amount,  # Overall discount applied
        'report_type': report_type,  # Send report type to the template
    }

    return render(request, 'admin_log/sales_report.html', context)