from django.shortcuts import render, redirect , get_object_or_404
from django.contrib.auth import login , logout
from django.views.decorators.cache import cache_control,never_cache
from django.utils import timezone
from datetime import timedelta
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail ,BadHeaderError
from django.conf import settings
from .forms import RegistrationForm, AccountAuthenticationForm, OTPForm , AddressForm, AccountUpdateForm
from .models import Account, OTP, Address
from product_management.models import Product , Category 
from django.db.models import Min, Max , Count
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
from django.core.exceptions import ObjectDoesNotExist
from orders.models import Order, OrderProduct





# Create your views here.
def index(request):
    return render(request, 'user_log/index.html')

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
    send_mail(subject, message, email_from, recipient_list)


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
                    return redirect('userlog:user_products')
                else:
                    form.add_error(None, "Invalid email or password")
            except Account.DoesNotExist:
                form.add_error(None, "Invalid email or password")
    else:
        form = AccountAuthenticationForm()
    
    return render(request, 'user_log/user_login.html', {'form': form})





def user_products(request):
    products = Product.objects.filter(deleted=False).prefetch_related('variants', 'category')
    categories = Category.objects.filter(is_deleted=False)
    new_products = Product.objects.filter(deleted=False).order_by('-id')[:3]

    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        products = products.filter(
            Q(title__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )

    # Category filter
    category = request.GET.get('category')
    if category:
        products = products.filter(category__name=category)

    # Sorting
    sort_by = request.GET.get('sort_by', 'featured')
    if sort_by == 'name_asc':
        products = products.order_by('title')
    elif sort_by == 'name_desc':
        products = products.order_by('-title')
    elif sort_by == 'price_asc':
        products = products.order_by('variants__price')
    elif sort_by == 'price_desc':
        products = products.order_by('-variants__price')
    # Add more sorting options as needed

    context = {
        'products': products,
        'categories': categories,
        'search_query': search_query,
        'selected_category': category,
        'sort_by': sort_by,
        'new_products': new_products,
    }
    return render(request, 'user_log/user_products.html', context)


def product_details(request, product_id):
    product = get_object_or_404(Product, id=product_id, deleted=False)
    variants = product.variants.filter(deleted=False)
    
    # Default selected color variant (e.g., the first variant)
    selected_variant = variants.first() if variants.exists() else None
    images = [selected_variant.image1, selected_variant.image2, selected_variant.image3] if selected_variant else []
    
    # Fetch similar products (same category, excluding the current product)
    similar_products = Product.objects.filter(
        category=product.category, deleted=False
    ).exclude(id=product.id)[:4]  # Display up to 4 similar products

    context = {
        'product': product,
        'variants': variants,
        'selected_variant': selected_variant,
        'images': images,
        'similar_products': similar_products,
    }
    return render(request, 'user_log/product_details.html', context)




@never_cache
def user_logout(request):
    logout(request)
    request.session.flush()
    return redirect('userlog:index') 


def about(request):
    return render(request,'user_log/about.html')







@login_required
def user_profile(request):
    user = request.user
    addresses = Address.objects.filter(account=user)
    
    context = {
        'user': user,
        'addresses': addresses,
    }
    return render(request, 'user_log/user_profile.html', context)

@login_required
def edit_user_profile(request):
    if request.method == 'POST':
        form = AccountUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('userlog:user_profile')
    else:
        form = AccountUpdateForm(instance=request.user)
    
    return render(request,'user_log/user_detail_update.html',{'form': form})


@login_required
def user_address_add(request):
    return render(request, 'user_log/user_address_add.html')




@login_required
def add_address(request):
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            return redirect('userlog:user_profile')
    else:
        form = AddressForm()
    return render(request, 'user_log/user_profile.html', {'form': form})

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
    context = {
        'address': address,
    }
    return render(request, 'user_log/delete_address.html', context)



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
    subject = 'Password Reset OTP'
    message = f'Your OTP for password reset is {otp}. It is valid for 5 minutes.'
    email_from = settings.EMAIL_HOST_USER
    recipient_list = [email]
    send_mail(subject, message, email_from, recipient_list)

def user_orders(request):
    return render(request,'user_log/user_orders.html')








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
    context = {
        'order': order,
        'order_items': order_items,
    }
    return render(request, 'user_log/user_order_details.html', context)

@login_required
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if order.status == 'New':
        order.status = 'Cancelled'
        order.save()
        messages.success(request, "Your order has been cancelled.")
    else:
        messages.error(request, "You cannot cancel this order.")
    return redirect('userlog:user_orders')

@login_required
def return_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if order.status == 'Delivered':
        order.status = 'Returned'
        order.save()
        messages.success(request, "Your order has been returned.")
    else:
        messages.error(request, "You cannot return this order.")
    return redirect('userlog:user_orders')
