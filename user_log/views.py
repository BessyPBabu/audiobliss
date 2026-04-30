import logging
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.cache import cache_control, never_cache

import services.user_service as user_service
import services.product_service as product_service
import services.wallet_service as wallet_service
from .forms import (
    RegistrationForm, AccountAuthenticationForm, OTPForm,
    AddressForm, AccountUpdateForm, EmailUpdateForm,
)
from .models import Account, Address

logger = logging.getLogger(__name__)


def index(request):
    return render(request, 'user_log/index.html')


def contact(request):
    return render(request, 'user_log/contact.html')


def about(request):
    return render(request, 'user_log/about.html')


# ─── Auth ─────────────────────────────────────────────────────────────────────

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def user_signup(request):
    if request.user.is_authenticated:
        return redirect('userlog:index')

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save(commit=False)
                user.set_password(form.cleaned_data['password1'])
                user.is_active = False
                user.save()
                user_service.create_and_send_otp(user)
                return redirect('userlog:verify_otp', user_id=user.id)
            except Exception:
                logger.exception("Signup error for email %s", form.cleaned_data.get('email'))
                messages.error(request, "An error occurred. Please try again.")
    else:
        form = RegistrationForm()

    return render(request, 'user_log/user_register.html', {'form': form})


def verify_otp(request, user_id):
    user = get_object_or_404(Account, id=user_id)
    message = ''

    if request.method == 'POST':
        if 'verify' in request.POST:
            form = OTPForm(request.POST)
            if form.is_valid():
                success, msg = user_service.verify_otp(user, form.cleaned_data['otp'])
                if success:
                    user_service.activate_user(user)
                    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                    return redirect('userlog:user_login')
                message = msg
            else:
                message = "Invalid OTP format."
        elif 'resend' in request.POST:
            if user_service.can_resend_otp(user):
                try:
                    user_service.create_and_send_otp(user)
                    message = "A new OTP has been sent to your email."
                except Exception:
                    logger.exception("Failed to resend OTP for user %s", user.id)
                    message = "Failed to send OTP. Please try again."
            else:
                message = "OTP was sent recently. Please wait before requesting again."

    return render(request, 'user_log/verify_otp.html', {'form': OTPForm(), 'message': message})


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def user_login(request):
    if request.user.is_authenticated:
        return redirect('userlog:index')

    if request.method == 'POST':
        form = AccountAuthenticationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            try:
                user = Account.objects.get(email=email)
                if not user.check_password(password):
                    messages.error(request, "Invalid email or password.")
                elif not user.is_active:
                    messages.error(request, "Your account has been blocked. Contact support.")
                else:
                    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                    return redirect('userlog:index')
            except Account.DoesNotExist:
                messages.error(request, "Invalid email or password.")
    else:
        form = AccountAuthenticationForm()

    return render(request, 'user_log/user_login.html', {'form': form})


@never_cache
def user_logout(request):
    logout(request)
    request.session.flush()
    return redirect('userlog:index')


# ─── Forgot Password ──────────────────────────────────────────────────────────

def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        try:
            user = Account.objects.get(email=email)
            user_service.create_and_send_otp(user)
            request.session['reset_email'] = email
            return redirect('userlog:verify_otp_forgot_password')
        except Account.DoesNotExist:
            messages.error(request, "No account found with this email address.")
        except Exception:
            logger.exception("Error in forgot_password for %s", email)
            messages.error(request, "Failed to send OTP. Please try again.")

    return render(request, 'user_log/forgot_password.html')


def verify_otp_forgot_password(request):
    email = request.session.get('reset_email')
    if not email:
        return redirect('userlog:forgot_password')

    try:
        user = Account.objects.get(email=email)
    except Account.DoesNotExist:
        messages.error(request, "Session expired. Please try again.")
        return redirect('userlog:forgot_password')

    if request.method == 'POST':
        entered_otp = request.POST.get('otp', '').strip()
        success, msg = user_service.verify_otp(user, entered_otp)
        if success:
            request.session['otp_verified'] = True
            return redirect('userlog:reset_password')
        messages.error(request, msg)

    return render(request, 'user_log/verify_otp_forgot_password.html')


def reset_password(request):
    if 'reset_email' not in request.session or not request.session.get('otp_verified'):
        return redirect('userlog:forgot_password')

    try:
        user = Account.objects.get(email=request.session['reset_email'])
    except Account.DoesNotExist:
        return redirect('userlog:forgot_password')

    if request.method == 'POST':
        password = request.POST.get('password', '')
        confirm = request.POST.get('confirm_password', '')
        if password != confirm:
            messages.error(request, "Passwords do not match.")
        elif len(password) < 8:
            messages.error(request, "Password must be at least 8 characters.")
        else:
            try:
                user_service.reset_user_password(user, password)
                request.session.pop('reset_email', None)
                request.session.pop('otp_verified', None)
                messages.success(request, "Password reset successfully.")
                return redirect('userlog:user_login')
            except Exception:
                logger.exception("Error resetting password for user %s", user.id)
                messages.error(request, "Failed to reset password.")

    return render(request, 'user_log/reset_password.html')


# ─── Products ─────────────────────────────────────────────────────────────────

def user_products(request):
    from product_management.models import Category
    try:
        queryset = product_service.get_annotated_products_queryset()
        search_query = request.GET.get('search', '').strip()
        category_name = request.GET.get('category', '').strip()
        sort_by = request.GET.get('sort_by', 'featured')

        queryset = product_service.apply_filters(queryset, search_query, category_name, sort_by)
        total_count = queryset.count()

        page_obj = product_service.paginate_queryset(queryset, request.GET.get('page'))
        product_service.enrich_products_with_offer_data(page_obj)

        categories = Category.objects.filter(is_deleted=False, is_active=True)
        new_products = product_service.get_annotated_products_queryset().order_by('-id')[:3]

        return render(request, 'user_log/user_products.html', {
            'products': page_obj,
            'categories': categories,
            'search_query': search_query,
            'selected_category': category_name,
            'sort_by': sort_by,
            'new_products': new_products,
            'total_product_count': total_count,
        })
    except Exception:
        logger.exception("Error loading user products page")
        messages.error(request, "Something went wrong. Please try again.")
        return render(request, 'user_log/user_products.html', {'products': [], 'categories': []})


def product_details(request, product_id):
    from product_management.models import Product
    from cart.models import WishlistItem
    from services.offer_service import (
        get_best_offer_for_product,
        apply_offer_to_price,
        get_discount_percentage_for_product,
    )
    from decimal import Decimal

    try:
        product = get_object_or_404(Product, id=product_id, deleted=False, is_active=True)
        variants = product.variants.filter(deleted=False, is_active=True).select_related('color')
        selected_variant = variants.first()

        original_price = None
        discounted_price = None
        discount_percentage = Decimal('0')

        if selected_variant:
            original_price = selected_variant.price
            discount_percentage = get_discount_percentage_for_product(product)
            discounted_price = apply_offer_to_price(
                original_price, get_best_offer_for_product(product)
            )

        # Attach offer price to each variant for JS data attributes
        for variant in variants:
            variant.offer_price = apply_offer_to_price(
                variant.price, get_best_offer_for_product(product)
            )

        similar_products = Product.objects.filter(
            category=product.category, deleted=False, is_active=True
        ).exclude(id=product.id).prefetch_related('variants')[:4]

        wishlist_variant_ids = []
        if request.user.is_authenticated:
            wishlist_variant_ids = list(
                WishlistItem.objects.filter(
                    wishlist__user=request.user,
                    product_variant__product_id=product_id,
                ).values_list('product_variant_id', flat=True)
            )

        return render(request, 'user_log/product_details.html', {
            'product': product,
            'variants': variants,
            'selected_variant': selected_variant,
            'similar_products': similar_products,
            'original_price': original_price,
            'discounted_price': discounted_price,
            'discount_percentage': discount_percentage,
            'wishlist_variant_ids': wishlist_variant_ids,
        })
    except Exception:
        logger.exception("Error loading product %s", product_id)
        messages.error(request, "Product not found or unavailable.")
        return redirect('userlog:user_products')


# ─── Profile ──────────────────────────────────────────────────────────────────

@login_required
def user_profile(request):
    addresses = Address.objects.filter(account=request.user)

    if request.method == 'POST':
        address_form = AddressForm(request.POST)
        if address_form.is_valid():
            try:
                address = address_form.save(commit=False)
                address.account = request.user
                address.save()
                messages.success(request, "Address added successfully.")
                return redirect('userlog:user_profile')
            except Exception:
                logger.exception("Error saving address for user %s", request.user.id)
                messages.error(request, "Failed to save address.")
    else:
        address_form = AddressForm()

    return render(request, 'user_log/user_profile.html', {
        'addresses': addresses,
        'address_form': address_form,
    })


@login_required
def edit_user_profile(request):
    if request.method == 'POST':
        form = AccountUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Profile updated successfully.")
                return redirect('userlog:user_profile')
            except Exception:
                logger.exception("Error updating profile for user %s", request.user.id)
                messages.error(request, "Failed to update profile.")
    else:
        form = AccountUpdateForm(instance=request.user)

    return render(request, 'user_log/user_detail_update.html', {'form': form})


@login_required
def edit_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, account=request.user)

    if request.method == 'POST':
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Address updated.")
                return redirect('userlog:user_profile')
            except Exception:
                logger.exception("Error updating address %s", address_id)
                messages.error(request, "Failed to update address.")
    else:
        form = AddressForm(instance=address)

    return render(request, 'user_log/edit_address.html', {'address_form': form, 'address': address})


@login_required
def delete_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, account=request.user)
    if request.method == 'POST':
        address.delete()
        messages.success(request, "Address deleted.")
    return redirect('userlog:user_profile')


@login_required
def update_email(request):
    if request.method == 'POST':
        form = EmailUpdateForm(request.POST)
        if form.is_valid():
            new_email = form.cleaned_data['new_email']
            try:
                user_service.initiate_email_update(request.user, new_email)
                request.session['new_email'] = new_email
                messages.success(request, "OTP sent to your new email address.")
                return redirect('userlog:verify_otp_email_update')
            except ValueError as e:
                messages.error(request, str(e))
            except Exception:
                logger.exception("Error initiating email update for user %s", request.user.id)
                messages.error(request, "Failed to send OTP. Please try again.")
    else:
        form = EmailUpdateForm()

    return render(request, 'user_log/update_email.html', {'form': form})


@login_required
def verify_otp_email_update(request):
    if request.method == 'POST':
        form = OTPForm(request.POST)
        if form.is_valid():
            success, msg = user_service.verify_otp(request.user, form.cleaned_data['otp'])
            if success:
                try:
                    user_service.confirm_email_update(request.user)
                    request.session.pop('new_email', None)
                    messages.success(request, "Email updated successfully.")
                    return redirect('userlog:user_profile')
                except ValueError as e:
                    messages.error(request, str(e))
                except Exception:
                    logger.exception("Error confirming email update for user %s", request.user.id)
                    messages.error(request, "Failed to update email.")
            else:
                messages.error(request, msg)
    else:
        form = OTPForm()

    return render(request, 'user_log/verify_otp.html', {'form': form})


# ─── Password Reset (logged in) ───────────────────────────────────────────────

@login_required
def reset_password_request(request):
    if request.method == 'POST':
        old_password = request.POST.get('old_password', '')
        user = authenticate(request, email=request.user.email, password=old_password)
        if user:
            try:
                user_service.create_and_send_otp(user)
                request.session['reset_email'] = user.email
                return redirect('userlog:reset_password_verify_otp')
            except Exception:
                logger.exception("Error sending OTP for password reset, user %s", request.user.id)
                messages.error(request, "Failed to send OTP.")
        else:
            messages.error(request, "Current password is incorrect.")

    return render(request, 'user_log/reset_password_request.html')


@login_required
def reset_password_verify_otp(request):
    email = request.session.get('reset_email')
    if not email:
        return redirect('userlog:reset_password_request')

    try:
        user = Account.objects.get(email=email)
    except Account.DoesNotExist:
        return redirect('userlog:reset_password_request')

    if request.method == 'POST':
        success, msg = user_service.verify_otp(user, request.POST.get('otp', '').strip())
        if success:
            request.session['otp_verified'] = True
            return redirect('userlog:reset_password_set_new')
        messages.error(request, msg)

    return render(request, 'user_log/reset_password_verify_otp.html')


@login_required
def reset_password_set_new(request):
    if 'reset_email' not in request.session or not request.session.get('otp_verified'):
        return redirect('userlog:reset_password_request')

    try:
        user = Account.objects.get(email=request.session['reset_email'])
    except Account.DoesNotExist:
        return redirect('userlog:reset_password_request')

    if request.method == 'POST':
        new_password = request.POST.get('new_password', '')
        confirm = request.POST.get('confirm_password', '')
        if new_password != confirm:
            messages.error(request, "Passwords do not match.")
        elif len(new_password) < 8:
            messages.error(request, "Password must be at least 8 characters.")
        else:
            try:
                user_service.reset_user_password(user, new_password)
                request.session.pop('reset_email', None)
                request.session.pop('otp_verified', None)
                messages.success(request, "Password updated successfully.")
                return redirect('userlog:user_login')
            except Exception:
                logger.exception("Error setting new password for user %s", user.id)
                messages.error(request, "Failed to update password.")

    return render(request, 'user_log/reset_password_set_new.html')


# ─── Orders ───────────────────────────────────────────────────────────────────

@login_required
def user_orders(request):
    from orders.models import Order
    orders = Order.objects.filter(
        user=request.user, is_ordered=True
    ).select_related('payment').order_by('-created_at')

    return render(request, 'user_log/user_orders.html', {'orders': orders})


@login_required
def order_details(request, order_id):
    from orders.models import Order, OrderProduct
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = OrderProduct.objects.filter(order=order).select_related(
        'product_variant__product', 'product_variant__color'
    )
    for item in order_items:
        item.total_price = item.product_price * item.quantity

    return render(request, 'user_log/user_order_details.html', {
        'order': order,
        'order_items': order_items,
    })


@login_required
def cancel_order(request, order_id):
    from orders.models import Order
    from orders.forms import CancelOrderForm
    from services.order_service import request_cancellation, OrderError

    order = get_object_or_404(Order, id=order_id, user=request.user)

    if request.method == 'POST':
        form = CancelOrderForm(request.POST)
        if form.is_valid():
            reason = form.cleaned_data.get('reason') or form.cleaned_data.get('custom_reason')
            try:
                request_cancellation(order, reason)
                messages.success(request, "Cancellation request submitted.")
                return redirect('userlog:user_orders')
            except OrderError as e:
                messages.error(request, str(e))
            except Exception:
                logger.exception("Error cancelling order %s", order_id)
                messages.error(request, "Failed to submit cancellation.")
    else:
        form = CancelOrderForm()

    return render(request, 'user_log/cancel_order.html', {'order': order, 'form': form})


@login_required
def return_order(request, order_id):
    from orders.models import Order
    from orders.forms import ReturnRequestForm
    from services.order_service import request_return, OrderError

    order = get_object_or_404(Order, id=order_id, user=request.user)

    if request.method == 'POST':
        form = ReturnRequestForm(request.POST)
        if form.is_valid():
            try:
                request_return(order, request.user, form.cleaned_data['reason'])
                messages.success(request, "Return request submitted.")
                return redirect('userlog:user_orders')
            except OrderError as e:
                messages.error(request, str(e))
            except Exception:
                logger.exception("Error submitting return for order %s", order_id)
                messages.error(request, "Failed to submit return request.")
    else:
        form = ReturnRequestForm()

    return render(request, 'user_log/return_request_form.html', {'order': order, 'form': form})


# ─── Wallet ────────────────────────────────────────────────────────────────────

@login_required
def wallet(request):
    try:
        balance = wallet_service.get_balance(request.user)
        history = wallet_service.get_transaction_history(request.user)
    except Exception:
        logger.exception("Error loading wallet for user %s", request.user.id)
        balance = 0
        history = []

    return render(request, 'user_log/wallet.html', {'balance': balance, 'wallethistory': history})
