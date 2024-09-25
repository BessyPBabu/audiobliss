from django.shortcuts import render, redirect , get_object_or_404
from django.contrib.auth import login , logout
from django.views.decorators.cache import cache_control,never_cache
from django.utils import timezone
from datetime import timedelta
from django.core.paginator import Paginator , PageNotAnInteger,EmptyPage
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail 
from django.conf import settings
from .forms import RegistrationForm, AccountAuthenticationForm, OTPForm , AddressForm, AccountUpdateForm, EmailUpdateForm
from .models import Account, OTP, Address, Wallet, WalletHistory
from product_management.models import Product , Category 
from django.db.models import Min, Max 
from django.contrib.auth import authenticate
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.backends import ModelBackend
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.db.models.query_utils import Q
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
import random
import string
from django.core.exceptions import ObjectDoesNotExist
from orders.models import Order, OrderProduct ,ReturnRequest
from orders.forms import CancelOrderForm , ReturnRequestForm
from offer_management.models import ProductOffer,CategoryOffer
from decimal import Decimal
from django.db.models import Q, Min, Max, F, ExpressionWrapper, DecimalField, Subquery, OuterRef,Value
from django.db.models.functions import Coalesce, Greatest
from cart.models import WishlistItem

import logging
logger = logging.getLogger(__name__)


# Create your views here.
def index(request):
    return render(request, 'user_log/index.html')


def contact(request):
    return render(request, 'user_log/contact.html')


def about(request):
    return render(request,'user_log/about.html')


#======================================= USER SIGNUP,LOGIN,LOGOUT START======================================================#


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def user_signup(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password1'])
            user.is_active = False  # User remains inactive until OTP is verified
            user.save()
            otp = OTP.objects.create(user=user)
            send_otp_via_email(user.email, otp.otp)
            return redirect('userlog:verify_otp', user_id=user.id)
    else:
        form = RegistrationForm()
    return render(request, 'user_log/user_register.html', {'form': form})


def verify_otp(request, user_id):
    user = Account.objects.get(id=user_id)
    message = ''
    form = OTPForm()
    
    if request.method == 'POST':
        if 'verify' in request.POST:
            form = OTPForm(request.POST)
            if form.is_valid():
                otp_code = form.cleaned_data['otp']
                otp = OTP.objects.filter(user=user, is_active=True).first()
                if otp and otp.otp == otp_code and (timezone.now() - otp.created_at) < timedelta(minutes=5):
                    user.is_active = True
                    user.save()
                    otp.is_active = False
                    otp.save()
                    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                    return redirect('userlog:user_login')
                else:
                    message = 'Invalid OTP or OTP has expired.'
        elif 'resend' in request.POST:
            otp = OTP.objects.filter(user=user, is_active=True).first()
            if otp and (timezone.now() - otp.created_at) < timedelta(minutes=5):
                message = 'OTP was sent recently. Please wait for a while before requesting again.'
            else:
                if otp:
                    otp.is_active = False
                    otp.save()
                otp = OTP.objects.create(user=user)
                send_otp_via_email(user.email, otp.otp)
                message = 'A new OTP has been sent to your email.'
    else:
        form = OTPForm()
    
    return render(request, 'user_log/verify_otp.html', {'form': form, 'message': message})


def send_otp_via_email(email, otp):
    subject = 'Your OTP Code'
    message = f'Your OTP code is {otp}. It is valid for 5 minutes.'
    email_from = settings.EMAIL_HOST_USER
    recipient_list = [email]
    try:
        send_mail(subject, message, email_from, recipient_list)
        logger.info(f"OTP email sent to {email}")
    except Exception as e:
        logger.error(f"Failed to send OTP email to {email}. Error: {str(e)}")


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def user_login(request):
    if request.method == 'POST':
        form = AccountAuthenticationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            try:
                user = Account.objects.get(email=email)
                if user.check_password(password):
                    # Specify the backend when logging in
                    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                    return redirect('userlog:index')
                else:
                    form.add_error(None, "Invalid email or password")
            except Account.DoesNotExist:
                form.add_error(None, "Invalid email or password")
    else:
        form = AccountAuthenticationForm()
    
    return render(request, 'user_log/user_login.html', {'form': form})


@never_cache
def user_logout(request):
    logout(request)
    request.session.flush()
    return redirect('userlog:index') 


#======================================= USER SIGNUP,LOGIN,LOGOUT END======================================================#


#======================================= USER PRODUCTS START======================================================#


def user_products(request):
    try:
        full_products_queryset = Product.objects.filter(deleted=False).prefetch_related('variants', 'category')
        categories = Category.objects.filter(is_deleted=False)
        new_products = Product.objects.filter(deleted=False).order_by('-id')[:3]

        # Annotate queryset with offer information
        full_products_queryset = full_products_queryset.annotate(
            product_discount=Subquery(
                ProductOffer.objects.filter(
                    product=OuterRef('pk'),
                    offer__is_active=True,
                    offer__start_date__lte=timezone.now(),
                    offer__end_date__gte=timezone.now()
                ).order_by('-offer__discount_percentage').values('offer__discount_percentage')[:1]
            ),
            product_offer_name=Subquery(
                ProductOffer.objects.filter(
                    product=OuterRef('pk'),
                    offer__is_active=True,
                    offer__start_date__lte=timezone.now(),
                    offer__end_date__gte=timezone.now()
                ).order_by('-offer__discount_percentage').values('offer__name')[:1]
            ),
            category_discount=Subquery(
                CategoryOffer.objects.filter(
                    category=OuterRef('category'),
                    offer__is_active=True,
                    offer__start_date__lte=timezone.now(),
                    offer__end_date__gte=timezone.now()
                ).order_by('-offer__discount_percentage').values('offer__discount_percentage')[:1]
            ),
            category_offer_name=Subquery(
                CategoryOffer.objects.filter(
                    category=OuterRef('category'),
                    offer__is_active=True,
                    offer__start_date__lte=timezone.now(),
                    offer__end_date__gte=timezone.now()
                ).order_by('-offer__discount_percentage').values('offer__name')[:1]
            ),
            best_discount=Greatest(
                Coalesce(F('product_discount'), Value(0, output_field=DecimalField())),
                Coalesce(F('category_discount'), Value(0, output_field=DecimalField())),
                output_field=DecimalField()
            ),
            min_variant_price=Min('variants__price'),
            discounted_price=ExpressionWrapper(
                F('min_variant_price') * (1 - F('best_discount') / 100),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        )

        # Search functionality
        search_query = request.GET.get('search', '')
        if search_query:
            full_products_queryset = full_products_queryset.filter(
                Q(title__icontains=search_query) |
                Q(category__name__icontains=search_query)
            )

        # Category filter
        category = request.GET.get('category')
        if category:
            full_products_queryset = full_products_queryset.filter(category__name=category)

        # Sorting
        sort_by = request.GET.get('sort_by', 'featured')
        if sort_by == 'name_asc':
            full_products_queryset = full_products_queryset.order_by('title')
        elif sort_by == 'name_desc':
            full_products_queryset = full_products_queryset.order_by('-title')
        elif sort_by == 'price_asc':
            full_products_queryset = full_products_queryset.annotate(
                min_price=Min('variants__price')
            ).order_by('min_price')
        elif sort_by == 'price_desc':
            full_products_queryset = full_products_queryset.annotate(
                max_price=Max('variants__price')
            ).order_by('-max_price')
        else:
            # Default ordering when no specific sorting is applied
            full_products_queryset = full_products_queryset.order_by('id')

        # Ensure we have unique products
        full_products_queryset = full_products_queryset.distinct()

        # Pagination
        paginator = Paginator(full_products_queryset, 6)  # Show 6 products per page
        page = request.GET.get('page')
        try:
            products = paginator.page(page)
        except PageNotAnInteger:
            products = paginator.page(1)
        except EmptyPage:
            products = paginator.page(paginator.num_pages)

        # Process each product after pagination
        for product in products:
            variant = product.variants.filter(is_active=True).first()
            if variant:
                product.original_price = product.min_variant_price
                product.discounted_price = product.discounted_price
                
                if product.best_discount > 0:
                    offer_name = product.product_offer_name if product.product_discount is not None else product.category_offer_name
                    product.active_offer = {
                        'discount_percentage': product.best_discount,
                        'name': offer_name,
                        'is_product_offer': product.product_discount is not None,
                        'is_category_offer': product.category_discount is not None
                    }
                else:
                    product.active_offer = None

                # Ensure prices are Decimal objects
                product.original_price = Decimal(product.original_price).quantize(Decimal('0.01'))
                product.discounted_price = Decimal(product.discounted_price).quantize(Decimal('0.01'))
            else:
                product.original_price = None
                product.discounted_price = None
                product.active_offer = None

        context = {
            'products': products,
            'categories': categories,
            'search_query': search_query,
            'selected_category': category,
            'sort_by': sort_by,
            'new_products': new_products,
            'total_product_count': full_products_queryset.count(),
        }
        return render(request, 'user_log/user_products.html', context)

    except Exception as e:
        # Log the error or return an error response
        print(f"Error in user_products view: {e}")
        return render(request, 'user_log/error.html', {'error': str(e)})


def product_details(request, product_id):
    product = get_object_or_404(Product, id=product_id, deleted=False)
    
    # Annotate the product with the best available discount (product or category)
    product = Product.objects.filter(id=product_id, deleted=False).annotate(
        product_discount=Subquery(
            ProductOffer.objects.filter(
                product=OuterRef('pk'),
                offer__is_active=True,
                offer__start_date__lte=timezone.now(),
                offer__end_date__gte=timezone.now()
            ).order_by('-offer__discount_percentage').values('offer__discount_percentage')[:1]
        ),
        category_discount=Subquery(
            CategoryOffer.objects.filter(
                category=OuterRef('category'),
                offer__is_active=True,
                offer__start_date__lte=timezone.now(),
                offer__end_date__gte=timezone.now()
            ).order_by('-offer__discount_percentage').values('offer__discount_percentage')[:1]
        ),
        best_discount=Greatest(
            Coalesce(F('product_discount'), Value(0, output_field=DecimalField())),
            Coalesce(F('category_discount'), Value(0, output_field=DecimalField())),
            output_field=DecimalField()
        )
    ).first()
    
    variants = product.variants.filter(deleted=False)
    
    # Default selected color variant (e.g., the first variant)
    selected_variant = variants.first() if variants.exists() else None
    
    if selected_variant:
        # Calculate the original price and discounted price
        original_price = selected_variant.price
        discount_percentage = product.best_discount or Decimal(0)
        discounted_price = original_price * (1 - discount_percentage / 100)
        
        # Ensure prices are rounded to 2 decimal places
        original_price = Decimal(original_price).quantize(Decimal('0.01'))
        discounted_price = Decimal(discounted_price).quantize(Decimal('0.01'))
        
        images = [selected_variant.image1, selected_variant.image2, selected_variant.image3]
    else:
        original_price = None
        discounted_price = None
        images = []

    # Fetch similar products (same category, excluding the current product)
    similar_products = Product.objects.filter(
        category=product.category, deleted=False
    ).exclude(id=product.id)[:4]  # Display up to 4 similar products

    # Get all variant IDs in the wishlist for this product
    wishlist_variant_ids = WishlistItem.objects.filter(
        wishlist__user=request.user, 
        product_variant__product_id=product_id
    ).values_list('product_variant_id', flat=True) if request.user.is_authenticated else []

    context = {
        'product': product,
        'variants': variants,
        'selected_variant': selected_variant,
        'images': images,
        'similar_products': similar_products,
        'original_price': original_price,
        'discounted_price': discounted_price,
        'discount_percentage': discount_percentage,
        'wishlist_variant_ids': list(wishlist_variant_ids),
    }
    return render(request, 'user_log/product_details.html', context)


#======================================= USER PRODUCT END======================================================#


#======================================= USER PROFILE START======================================================#


@login_required
def user_profile(request):
    user = request.user
    addresses = Address.objects.filter(account=user)
    
    if request.method == 'POST':
        address_form = AddressForm(request.POST)
        if address_form.is_valid():
            address = address_form.save(commit=False)
            address.account = user
            address.save()
            return redirect('userlog:user_profile')
    else:
        address_form = AddressForm()
    
    context = {
        'user': user,
        'addresses': addresses,
        'address_form': address_form,
    }
    return render(request, 'user_log/user_profile.html', context)


@login_required
def edit_user_profile(request):
    if request.method == 'POST':
        form = AccountUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('userlog:user_profile')
    else:
        form = AccountUpdateForm(instance=request.user)
    
    return render(request, 'user_log/user_detail_update.html', {'form': form})


@login_required
def edit_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, account=request.user)
    
    if request.method == 'POST':
        address_form = AddressForm(request.POST, instance=address)
        if address_form.is_valid():
            address_form.save()
            return redirect('userlog:user_profile')
    else:
        address_form = AddressForm(instance=address)
    
    context = {
        'address_form': address_form,
        'address': address,
    }
    return render(request, 'user_log/edit_address.html', context)


@login_required
def delete_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, account=request.user)
    if request.method == 'POST':
        address.delete()
        return redirect('userlog:user_profile')
    return redirect('userlog:user_profile')


def forgot_password(request):
    if request.method == "POST":
        email = request.POST["email"]
        try:
            user = Account.objects.get(email=email)
            otp = OTP.objects.create(user=user)
            send_otp_via_email(user.email, otp.otp)
            request.session['reset_email'] = email
            return redirect('userlog:verify_otp_forgot_password')
        except Account.DoesNotExist:
            messages.error(request, "No account found with this email address.")
    return render(request, 'user_log/forgot_password.html')


def verify_otp_forgot_password(request):
    if 'reset_email' not in request.session:
        return redirect('userlog:forgot_password')
    
    email = request.session['reset_email']
    user = Account.objects.get(email=email)
    
    if request.method == "POST":
        entered_otp = request.POST.get('otp')
        otp = OTP.objects.filter(user=user, is_active=True).first()
        
        if otp and otp.otp == entered_otp and (timezone.now() - otp.created_at) < timedelta(minutes=5):
            otp.is_active = False
            otp.save()
            request.session['otp_verified'] = True
            return redirect('userlog:reset_password')
        else:
            messages.error(request, "Invalid OTP or OTP has expired.")
    
    return render(request, 'user_log/verify_otp_forgot_password.html')


def reset_password(request):
    if 'reset_email' not in request.session or 'otp_verified' not in request.session:
        return redirect('userlog:forgot_password')
    
    email = request.session['reset_email']
    user = Account.objects.get(email=email)
    
    if request.method == "POST":
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        if password == confirm_password:
            user.set_password(password)
            user.save()
            del request.session['reset_email']
            del request.session['otp_verified']
            messages.success(request, "Password has been reset successfully.")
            return redirect('userlog:user_login')
        else:
            messages.error(request, "Passwords do not match.")
    
    return render(request, 'user_log/reset_password.html')


def send_otp_via_email(email, otp):
    subject = 'OTP Verification'
    message = f'Your OTP  is {otp}. It is valid for 5 minutes.'
    email_from = settings.EMAIL_HOST_USER
    recipient_list = [email]
    send_mail(subject, message, email_from, recipient_list)


def user_orders(request):
    return render(request,'user_log/user_orders.html')


def update_email(request):
    if request.method == 'POST':
        form = EmailUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            user = form.save(commit=False)
            new_email = form.cleaned_data.get('new_email')

            # Create a new OTP instance
            otp_code = ''.join(random.choices(string.digits, k=6))  # Generate a 6-digit OTP
            otp_instance = OTP.objects.create(user=user, otp=otp_code)

            # Send OTP to the new email address
            send_otp_via_email(new_email, otp_instance.otp)

            # Store the new email in session or some temporary place to verify it later
            request.session['new_email'] = new_email

            messages.success(request, 'OTP has been sent to your new email address. Please verify.')
            return redirect('userlog:verify_otp_email_update')  # Redirect to the OTP verification page
    else:
        form = EmailUpdateForm(instance=request.user)
    
    return render(request, 'user_log/update_email.html', {'form': form})


def verify_otp_email_update(request):
    if request.method == 'POST':
        form = OTPForm(request.POST)
        if form.is_valid():
            otp_input = form.cleaned_data['otp']
            try:
                otp_instance = OTP.objects.get(user=request.user, otp=otp_input, is_active=True)
                # Optionally check if OTP is within the valid time window (e.g., 5 minutes)

                # Update the user's email address
                new_email = request.session.get('new_email')
                if new_email:
                    request.user.email = new_email
                    request.user.save()

                    # Deactivate the OTP
                    otp_instance.is_active = False
                    otp_instance.save()

                    # Clear the session
                    del request.session['new_email']

                    messages.success(request, 'Your email has been updated successfully.')
                    return redirect('userlog:user_profile')
                else:
                    messages.error(request, 'No new email found in the session.')

            except OTP.DoesNotExist:
                messages.error(request, 'Invalid or expired OTP.')
    else:
        form = OTPForm()
    
    return render(request, 'user_log/verify_otp.html', {'form': form})


def reset_password_request(request):
    if request.method == "POST":
        email = request.POST.get("email")
        old_password = request.POST.get("old_password")
        
        try:
            user = Account.objects.get(email=email)
            if authenticate(email=email, password=old_password):
                otp = OTP.objects.create(user=user)
                send_otp_via_email(user.email, otp.otp)
                request.session['reset_email'] = email
                return redirect('userlog:reset_password_verify_otp')
            else:
                messages.error(request, "Invalid email or password.")
        except Account.DoesNotExist:
            messages.error(request, "No account found with this email address.")
    
    return render(request, 'user_log/reset_password_request.html')


def reset_password_verify_otp(request):
    if 'reset_email' not in request.session:
        return redirect('userlog:reset_password_request')
    
    email = request.session['reset_email']
    user = Account.objects.get(email=email)
    
    if request.method == "POST":
        entered_otp = request.POST.get('otp')
        otp = OTP.objects.filter(user=user, is_active=True).first()
        
        if otp and otp.otp == entered_otp and (timezone.now() - otp.created_at) < timedelta(minutes=5):
            otp.is_active = False
            otp.save()
            request.session['otp_verified'] = True
            return redirect('userlog:reset_password_set_new')
        else:
            messages.error(request, "Invalid OTP or OTP has expired.")
    
    return render(request, 'user_log/reset_password_verify_otp.html')


def reset_password_set_new(request):
    if 'reset_email' not in request.session or 'otp_verified' not in request.session:
        return redirect('userlog:reset_password_request')
    
    email = request.session['reset_email']
    user = Account.objects.get(email=email)
    
    if request.method == "POST":
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if new_password == confirm_password:
            user.set_password(new_password)
            user.save()
            del request.session['reset_email']
            del request.session['otp_verified']
            messages.success(request, "Password has been reset successfully.")
            return redirect('userlog:user_login')
        else:
            messages.error(request, "Passwords do not match.")
    
    return render(request, 'user_log/reset_password_set_new.html')


#======================================= USER PROFILE END======================================================#


#======================================= USER ORDERS START======================================================#


@login_required
def user_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    context = {
        'orders': orders,
    }
    return render(request, 'user_log/user_orders.html', context)


@login_required
def order_details(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = OrderProduct.objects.filter(order=order)
    
    # Calculate total price for each item
    for item in order_items:
        item.total_price = item.product_price * item.quantity
    context = {
        'order': order,
        'order_items': order_items,
    }
    return render(request, 'user_log/user_order_details.html', context)


@login_required
def cancel_order(request, order_id):
    # Get the order and ensure it belongs to the logged-in user
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if request.method == 'POST':
        form = CancelOrderForm(request.POST)
        if form.is_valid():
            reason = form.cleaned_data.get('reason') or form.cleaned_data.get('custom_reason')
            
            # Set the cancellation request
            order.cancel_reason = reason
            order.status = 'Pending Cancellation'
            order.is_cancel_requested = True
            order.save()
            
            messages.success(request, "Your cancellation request has been submitted. Please wait for admin confirmation.")
            return redirect('userlog:user_orders')
    else:
        form = CancelOrderForm()

    return render(request, 'user_log/cancel_order.html', {'order': order, 'form': form})


@login_required
def return_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Check if a return request already exists for this order
    existing_request = ReturnRequest.objects.filter(order=order).first()
    if existing_request:
        messages.info(request, "A return request for this order already exists.")
        return redirect('userlog:user_orders')
    
    if order.status != 'Delivered':
        messages.error(request, "You can only return orders that have been delivered.")
        return redirect('userlog:user_orders')
    
    if request.method == 'POST':
        form = ReturnRequestForm(request.POST)
        if form.is_valid():
            return_request = form.save(commit=False)
            return_request.order = order
            return_request.user = request.user
            return_request.save()
            
            order.status = 'Return Requested'
            order.save()
            
            messages.success(request, "Your return request has been submitted and is pending approval.")
            return redirect('userlog:user_orders')
    else:
        form = ReturnRequestForm()
    
    context = {
        'order': order,
        'form': form,
    }
    return render(request, 'user_log/return_request_form.html', context)


#======================================= USER ORDERS END======================================================#


#======================================= USER WALLET START======================================================#


@login_required
def wallet(request):
    wallet, created = Wallet.objects.get_or_create(user=request.user)
    wallet_history = WalletHistory.objects.filter(wallet=wallet).order_by('-created_at')

    # Calculate balance by iterating over transactions
    balance = 0
    for transaction in wallet_history:
        if transaction.type == 'Refund':  # Add positive amounts (like refunds)
            balance += transaction.amount
        else:  # Subtract negative amounts (like payments)
            balance -= transaction.amount
    
    context = {
        'wallet': wallet,
        'balance': balance,
        'wallethistory': wallet_history,
    }
    return render(request, 'user_log/wallet.html', context)