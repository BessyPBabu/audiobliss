from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_GET
from .models import Product, ProductVariant, Color, Category,Brand
from .forms import ProductForm, ProductVariantForm, ColorForm, CategoryForm,BrandForm
from django.db import IntegrityError
from django.http import JsonResponse
from django.db.models import Prefetch
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


#------------------------------------CATEGORY------------------------------------------#

def category_list(request):
    categories = Category.objects.filter(is_deleted=False)  # Filter by is_active
    form = CategoryForm()
    return render(request, 'admin_log/category_list.html', {'categories': categories, 'form': form})

def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                return JsonResponse({'success': True, 'message': 'Category created successfully.'})
            except IntegrityError:
                errors = form.errors.as_json()
                return JsonResponse({'success': False, 'message': 'Category already exists.', 'errors': errors})
        else:
            errors = form.errors.as_json()
            return JsonResponse({'success': False, 'message': 'Invalid form data.', 'errors': errors})
    else:
        form = CategoryForm()
    
    categories = Category.objects.filter(is_deleted=False, is_active=True)
    return render(request, 'admin_log/category_list.html', {'form': form, 'categories': categories})

def category_update(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Category successfully updated!", extra_tags='category')
                return redirect('product_det:categories')
            except IntegrityError:
                messages.error(request, "A category with this name already exists.", extra_tags='category')
        else:
            messages.error(request, "Invalid form data.", extra_tags='category')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'admin_log/category_form.html', {'form': form})

def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        category.is_deleted = True
        category.is_active = False  # Optionally set as inactive
        category.save()
        messages.success(request, f'Category "{category.name}" has been deleted.', extra_tags='category')
        return redirect('product_det:categories')
    
    return render(request, 'admin_log/category_confirm_delete.html', {'category': category})

#------------------------------------CATEGORY------------------------------------------#


#------------------------------------PRODUCT------------------------------------------#

from django.db.models import Prefetch
from .models import Product, ProductVariant

def product_details(request):
    products = Product.objects.filter(deleted=False).select_related('category').prefetch_related(
        Prefetch('variants', queryset=ProductVariant.objects.filter(deleted=False))
    )
    for product in products:
        if not product.category.is_active:
            product.is_active = False
            product.save()

        # Check brand status
        if product.brand and not product.brand.is_active:
            product.is_active = False
            product.save()
        
        # Use product.variants.all() to get a queryset of variants
        variants = product.variants.all()
        if not product.is_active:
            for variant in variants:
                variant.is_active = False
                variant.save()
    # Fetch all brands for additional context if needed
    brands = Brand.objects.all()


    return render(request, 'admin_log/page-products-details.html', {'products': products,'brands': brands})


def add_product(request):

    form = ProductForm()
    brand_form = BrandForm()

    if request.method == 'POST':
        if 'add_brand' in request.POST:
            brand_form = BrandForm(request.POST)
            if brand_form.is_valid():
                brand_form.save()
                messages.success(request, 'Brand added successfully.', extra_tags='addbrand')
                return redirect('product_det:add_product')
            else:
                for field, errors in brand_form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field.capitalize()}: {error}", extra_tags='addbrand')
        else:
            form = ProductForm(request.POST, request.FILES)
            if form.is_valid():
                try:
                    product = form.save()
                    messages.success(request, 'Product added successfully.', extra_tags='addproduct')
                    return redirect('product_det:product_details')
                except IntegrityError:
                    messages.error(request, "Product with this title already exists.", extra_tags='addproduct')
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field.capitalize()}: {error}", extra_tags='addproduct')
 
    
    return render(request, 'admin_log/add_product.html', {'form': form, 'brand_form': brand_form})

def product_update(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        
        if form.is_valid():
            form.save()
            messages.success(request, 'Product updated successfully.', extra_tags='productupdate')
            return redirect('product_det:product_details')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.capitalize()}: {error}", extra_tags='productupdate')
    else:
        form = ProductForm(instance=product)

    return render(request, 'admin_log/product_update.html', {'form': form, 'product': product})

def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.deleted = True
        product.is_active = False  # Optionally set as inactive
        product.save()
        messages.success(request, f'Product "{product.title}" has been deleted.', extra_tags='productdelete')
        return redirect('product_det:product_details')
    return render(request, 'admin_log/product_delete.html', {'product': product})

def brand_update(request, id):
    brand = get_object_or_404(Brand, id=id)
    if request.method == "POST":
        form = BrandForm(request.POST, instance=brand)
        if form.is_valid():
            form.save()
            return redirect('product_det:product_details')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.capitalize()}: {error}")
    else:
        form = BrandForm(instance=brand)
    return render(request, 'admin_log/edit_brand.html', {'brand': brand, 'form': form})



def brand_delete(request, id):
    brand = get_object_or_404(Brand, id=id)
    if request.method == "POST":
        brand.delete()
        return redirect('product_det:product_details')
    return render(request, 'admin_log/delete_brand.html', {'brand': brand})


#------------------------------------PRODUCT------------------------------------------#


#------------------------------------VARIANTS------------------------------------------#

def add_variants(request):
    if request.method == 'POST':
        variant_form = ProductVariantForm(request.POST, request.FILES)
        color_form = ColorForm(request.POST)
        if 'add_variant' in request.POST:
            if variant_form.is_valid():
                variant = variant_form.save(commit=False)
                variant.save()
                messages.success(request, 'Variant added successfully.', extra_tags='variant')
                return redirect('product_det:variant_details')
            else:
                messages.error(request, "Invalid variant data.", extra_tags='variant')
        elif 'add_color' in request.POST:
            if color_form.is_valid():
                color = color_form.save()
                messages.success(request, 'Color added successfully.', extra_tags='color')
                return redirect('product_det:add_variants')
            else:
                messages.error(request, "Invalid color data.", extra_tags='color')
    else:
        variant_form = ProductVariantForm()
        color_form = ColorForm()

    return render(request, 'admin_log/add_variants.html', {
        'variant_form': variant_form,
        'color_form': color_form,
       
    })

@require_GET
def filter_products(request):
    brand_id = request.GET.get('brand_id')
    if brand_id:
        products = Product.objects.filter(brand_id=brand_id).values('id', 'title')
        return JsonResponse(list(products), safe=False)
    return JsonResponse([], safe=False)


def variant_details(request):
    variants = ProductVariant.objects.filter(deleted=False).select_related('product__category')
    for variant in variants:
        if not variant.product.category.is_active or not variant.product.is_active:
            variant.is_active = False
            variant.save()

    # Pagination logic
    paginator = Paginator(variants, 10)  # Show 10 variants per page
    page = request.GET.get('page')
    
    try:
        variants_paginated = paginator.page(page)
    except PageNotAnInteger:
        variants_paginated = paginator.page(1)  # If page is not an integer, deliver first page
    except EmptyPage:
        variants_paginated = paginator.page(paginator.num_pages)  # If page is out of range, deliver last page

    return render(request, 'admin_log/variant_details.html', {'variants': variants_paginated})

def edit_variant(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    
    if request.method == 'POST':
        variant_form = ProductVariantForm(request.POST, request.FILES, instance=variant)
        
        if variant_form.is_valid():
            try:
                # Save the form, which will trigger the model's clean method
                variant_form.save()
                messages.success(request, 'Variant updated successfully.', extra_tags='variant')
                return redirect('product_det:variant_details')
            except ValidationError as e:
                # Capture the validation errors and show them as messages
                messages.error(request, f"Error: {e.message}", extra_tags='variant')
            except IntegrityError:
                messages.error(request, "Variant with this data already exists.", extra_tags='variant')
        else:
            messages.error(request, "Invalid variant data.", extra_tags='variant')
    
    else:
        variant_form = ProductVariantForm(instance=variant)

    return render(request, 'admin_log/edit_variant.html', {
        'variant_form': variant_form,
        'variant': variant,
    })

def delete_variant(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    if request.method == 'POST':
        variant.deleted = True
        variant.is_active = False  # Optionally set as inactive
        variant.save()
        messages.success(request, 'Variant deleted successfully.', extra_tags='variant')
        return redirect('product_det:variant_details')
    return render(request, 'admin_log/delete_variant.html', {
        'variant': variant,
    })

#------------------------------------VARIANTS------------------------------------------#