from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Product, ProductVariant, Color, Category
from .forms import ProductForm, ProductVariantForm, ColorForm, CategoryForm
from django.db import IntegrityError


def category_list(request):
    categories = Category.objects.filter(is_deleted=False)
    form = CategoryForm()
    return render(request, 'admin_log/category_list.html', {'categories': categories, 'form': form})


def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Category successfully added!", extra_tags='category')
                return redirect('product_det:categories')
            except IntegrityError:
                messages.error(request, "A category with this name already exists.", extra_tags='category')
    else:
        form = CategoryForm()
    return render(request, 'admin_log/category_list.html', {'form': form})

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
        form = CategoryForm(instance=category)
    return render(request, 'admin_log/category_form.html', {'form': form})


def category_delete(request, pk):
    # This view remains largely unchanged
    category = get_object_or_404(Category, pk=pk)
    
    if request.method == 'POST':
        category.is_deleted = True
        category.save()
        messages.success(request, f'Category "{category.name}" has been deleted.',extra_tags='category')
        return redirect('product_det:categories')
    
    return render(request, 'admin_log/category_confirm_delete.html', {'category': category})



def product_details(request):
    products = Product.objects.filter(deleted=False)
    return render(request, 'admin_log/page-products-details.html', {'products': products})


def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            messages.success(request, 'Product added successfully.', extra_tags='addproduct')
            return redirect('product_det:product_details')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.capitalize()}: {error}", extra_tags='addproduct')
    else:
        form = ProductForm()
    
    return render(request, 'admin_log/add_product.html', {'form': form})

    
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
        product.save()
        messages.success(request, f'Product "{product.title}" has been deleted.', extra_tags='productdelete')
        return redirect('product_det:product_details')
    return render(request, 'admin_log/product_delete.html', {'product': product})
    


# def add_varients(request):
#     return render(request, 'admin_log/add_varients.html')

# def varient_details(request):
#     return render(request, 'admin_log/varient_details.html')


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
        elif 'add_color' in request.POST:
            if color_form.is_valid():
                color = color_form.save()
                messages.success(request, 'Color added successfully.', extra_tags='color')
                return redirect('product_det:add_variants')
    else:
        variant_form = ProductVariantForm()
        color_form = ColorForm()

    return render(request, 'admin_log/add_variants.html', {
        'variant_form': variant_form,
        'color_form': color_form,
    })

def variant_details(request):
    variants = ProductVariant.objects.filter(deleted=False)
    return render(request, 'admin_log/variant_details.html', {
        'variants': variants,
    })

def edit_variant(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    if request.method == 'POST':
        variant_form = ProductVariantForm(request.POST, request.FILES, instance=variant)
        if variant_form.is_valid():
            variant_form.save()
            messages.success(request, 'Variant updated successfully.', extra_tags='variant')
            return redirect('product_det:variant_details')
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
        variant.save()
        messages.success(request, 'Variant deleted successfully.', extra_tags='variant')
        return redirect('product_det:variant_details')
    return render(request, 'admin_log/delete_variant.html', {
        'variant': variant,
    })