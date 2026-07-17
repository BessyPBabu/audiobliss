import logging
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout as auth_logout
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Sum, Count
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.cache import cache_control, never_cache
from django.views.decorators.csrf import csrf_protect

import services.report_service as report_service
import services.order_service as order_service
import services.security_service as security_service
from admin_log.decorators import admin_required
from orders.models import Order, OrderProduct, ReturnRequest
from orders.forms import OrderForm
from user_log.models import Account
from product_management.models import Product

logger = logging.getLogger(__name__)

LOGIN_THROTTLE_KEY = 'admin_login'


# ─── Auth ─────────────────────────────────────────────────────────────────────

@csrf_protect
def admin_login(request):
    if request.user.is_authenticated and request.user.is_admin:
        return redirect('adminlog:admin_dashboard')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')

        if security_service.is_locked_out(LOGIN_THROTTLE_KEY, email):
            messages.error(
                request,
                "Too many failed login attempts. Please try again in 15 minutes.",
                extra_tags='login_error',
            )
            return render(request, 'admin_log/admin_login.html')

        user = authenticate(request, email=email, password=password)
        if user is not None and user.is_admin:
            security_service.clear_attempts(LOGIN_THROTTLE_KEY, email)
            login(request, user)
            logger.info("Admin %s logged in", email)
            return redirect('adminlog:admin_dashboard')

        security_service.register_failed_attempt(LOGIN_THROTTLE_KEY, email)
        logger.warning("Failed admin login attempt for %s", email)
        messages.error(request, "Invalid email or password.", extra_tags='login_error')

    return render(request, 'admin_log/admin_login.html')


@never_cache
def admin_logout(request):
    logger.info("Admin %s logged out", request.user.email if request.user.is_authenticated else 'unknown')
    auth_logout(request)
    return redirect('adminlog:admin_login')


def base(request):
    return render(request, 'admin_log/base.html')


# ─── Dashboard ────────────────────────────────────────────────────────────────

@admin_required
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def admin_dashboard(request):
    try:
        revenue = Order.objects.filter(is_ordered=True).aggregate(
            total=Sum('order_total')
        )['total'] or 0
        orders_count = Order.objects.filter(is_ordered=True).count()
        product_count = Product.objects.filter(deleted=False).count()
        total_users_count = Account.objects.filter(is_superuser=False).count()
        last_orders = Order.objects.filter(is_ordered=True).select_related(
            'user', 'payment'
        ).order_by('-created_at')[:5]

        chart_data = report_service.get_dashboard_chart_data()
    except Exception:
        logger.exception("Error loading admin dashboard")
        chart_data = {
            'dates': [], 'counts': [], 'monthlyDates': [], 'monthlyCounts': [],
            'yearlyDates': [], 'yearlyCounts': [], 'statusLabels': [], 'orderCounts': [],
            'best_selling_products': [], 'best_selling_categories': [], 'best_selling_brands': [],
        }
        revenue = orders_count = product_count = total_users_count = 0
        last_orders = []

    return render(request, 'admin_log/index.html', {
        'revenue': revenue,
        'orders_count': orders_count,
        'product_count': product_count,
        'total_users_count': total_users_count,
        'last_orders': last_orders,
        **chart_data,
    })


# ─── Users ────────────────────────────────────────────────────────────────────

@admin_required
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def users_list(request):
    search_query = request.GET.get('query', '').strip()
    user_qs = Account.objects.filter(is_superuser=False).order_by('id')
    if search_query:
        user_qs = user_qs.filter(username__icontains=search_query)

    paginator = Paginator(user_qs, 10)
    page = request.GET.get('page')
    try:
        users = paginator.page(page)
    except (EmptyPage, PageNotAnInteger):
        users = paginator.page(1)

    return render(request, 'admin_log/users_list.html', {'users': users})


@admin_required
def block_unblock_user(request, user_id):
    user = get_object_or_404(Account, id=user_id)
    try:
        user.toggle_active()
        status = "unblocked" if user.is_active else "blocked"
        logger.info("Admin %s %s user %s", request.user.email, status, user_id)
    except Exception:
        logger.exception("Error toggling user %s status", user_id)
        messages.error(request, "Failed to update user status.")

    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


# ─── Orders ───────────────────────────────────────────────────────────────────

@admin_required
def order_list(request):
    orders_qs = Order.objects.filter(is_ordered=True).select_related(
        'user', 'payment'
    ).order_by('-created_at')

    paginator = Paginator(orders_qs, 10)
    page = request.GET.get('page')
    try:
        orders = paginator.page(page)
    except (EmptyPage, PageNotAnInteger):
        orders = paginator.page(1)

    return render(request, 'admin_log/order_details.html', {'orders': orders})


@admin_required
def order_details(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order_items = OrderProduct.objects.filter(order=order).select_related(
        'product_variant__product', 'product_variant__color'
    )
    pending_requests = ReturnRequest.objects.filter(order=order, status='Pending')
    order_form = OrderForm(instance=order)

    if request.method == 'POST':
        if 'update_order' in request.POST:
            order_form = OrderForm(request.POST, instance=order)
            if order_form.is_valid():
                try:
                    updated_order = order_form.save()
                    if updated_order.status == 'Cancelled' and not updated_order.is_refunded:
                        order_service.confirm_cancellation(updated_order)
                    messages.success(request, "Order updated successfully.")
                    return redirect('adminlog:order_list')
                except Exception:
                    logger.exception("Error updating order %s", order_id)
                    messages.error(request, "Failed to update order.")
            else:
                messages.error(request, "Invalid form data.")

        elif 'approve_return' in request.POST:
            return_request_id = request.POST.get('return_request_id')
            return_request = get_object_or_404(ReturnRequest, id=return_request_id)
            try:
                order_service.approve_return(return_request)
                messages.success(request, f"Return #{return_request_id} approved and refund issued.")
            except order_service.OrderError as e:
                messages.error(request, str(e))
            except Exception:
                logger.exception("Error approving return %s", return_request_id)
                messages.error(request, "Failed to approve return.")
            return redirect('adminlog:order_list')

        elif 'reject_return' in request.POST:
            return_request_id = request.POST.get('return_request_id')
            return_request = get_object_or_404(ReturnRequest, id=return_request_id)
            try:
                order_service.reject_return(return_request)
                messages.success(request, f"Return #{return_request_id} rejected.")
            except order_service.OrderError as e:
                messages.error(request, str(e))
            except Exception:
                logger.exception("Error rejecting return %s", return_request_id)
                messages.error(request, "Failed to reject return.")
            return redirect('adminlog:order_list')

    return render(request, 'admin_log/page_orders_detail.html', {
        'order': order,
        'order_items': order_items,
        'order_form': order_form,
        'pending_requests': pending_requests,
    })


# ─── Sales Report ─────────────────────────────────────────────────────────────

@admin_required
def sales_report(request):
    report_type = request.GET.get('report_type', '30days')
    start_date, end_date = report_service.get_date_range(
        report_type,
        request.GET.get('start_date'),
        request.GET.get('end_date'),
    )

    try:
        orders = report_service.get_orders_for_range(start_date, end_date)
        metrics = report_service.calculate_metrics(orders)

        paginator = Paginator(orders, 10)
        page = request.GET.get('page')
        try:
            page_obj = paginator.page(page)
        except (EmptyPage, PageNotAnInteger):
            page_obj = paginator.page(1)

        order_data = report_service.build_order_data(page_obj)
    except Exception:
        logger.exception("Error generating sales report")
        metrics = {'total_sales_count': 0, 'total_order_amount': 0, 'total_discount_amount': 0}
        order_data = []
        page_obj = None

    return render(request, 'admin_log/sales_report.html', {
        'order_data': order_data,
        'page_obj': page_obj,
        'start_date_value': start_date.strftime('%Y-%m-%d'),
        'end_date_value': end_date.strftime('%Y-%m-%d'),
        'report_type': report_type,
        **metrics,
    })