import logging
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_GET

from admin_log.decorators import admin_required
from .models import Product, ProductVariant, Color, Category, Brand
from .forms import ProductForm, ProductVariantForm, ColorForm, CategoryForm, BrandForm

logger = logging.getLogger(__name__)


# ─── Category ─────────────────────────────────────────────────────────────────

@admin_required
def category_list(request):
    categories = Category.objects.filter(is_deleted=False)
    form = CategoryForm()
    return render(request, 'admin_log/category_list.html', {'categories': categories, 'form': form})


@admin_required
def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                return JsonResponse({'success': True, 'message': 'Category created successfully.'})
            except IntegrityError:
                logger.warning("Duplicate category name attempted")
                return JsonResponse({'success': False, 'message': 'Category already exists.'})
        return JsonResponse({'success': False, 'message': 'Invalid form data.', 'errors': form.errors.as_json()})

    form = CategoryForm()
    categories = Category.objects.filter(is_deleted=False, is_active=True)
    return render(request, 'admin_log/category_list.html', {'form': form, 'categories': categories})


@admin_required
def category_update(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Category updated successfully.")
                return redirect('product_det:categories')
            except IntegrityError:
                messages.error(request, "A category with this name already exists.")
        else:
            messages.error(request, "Invalid form data.")
    else:
        form = CategoryForm(instance=category)

    return render(request, 'admin_log/category_form.html', {'form': form})


@admin_required
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        try:
            category.soft_delete()
            messages.success(request, f'Category "{category.name}" deleted.')
        except Exception:
            logger.exception("Error deleting category %s", pk)
            messages.error(request, "Failed to delete category.")
        return redirect('product_det:categories')

    return render(request, 'admin_log/category_confirm_delete.html', {'category': category})


# ─── Product ──────────────────────────────────────────────────────────────────

@admin_required
def product_details(request):
    products = Product.objects.filter(deleted=False).select_related('category', 'brand')
    brands = Brand.objects.filter(is_deleted=False)
    return render(request, 'admin_log/page-products-details.html', {
        'products': products,
        'brands': brands,
    })


@admin_required
def add_product(request):
    form = ProductForm()
    brand_form = BrandForm()

    if request.method == 'POST':
        if 'add_brand' in request.POST:
            brand_form = BrandForm(request.POST)
            if brand_form.is_valid():
                try:
                    brand_form.save()
                    messages.success(request, 'Brand added successfully.', extra_tags='addbrand')
                except Exception:
                    logger.exception("Error adding brand")
                    messages.error(request, 'Failed to add brand.', extra_tags='addbrand')
            else:
                for error in brand_form.errors.values():
                    messages.error(request, error.as_text(), extra_tags='addbrand')
            return redirect('product_det:add_product')

        form = ProductForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Product added successfully.', extra_tags='addproduct')
                return redirect('product_det:product_details')
            except IntegrityError:
                messages.error(request, "Product with this title already exists.", extra_tags='addproduct')
            except Exception:
                logger.exception("Error adding product")
                messages.error(request, "Failed to add product.", extra_tags='addproduct')
        else:
            for error in form.errors.values():
                messages.error(request, error.as_text(), extra_tags='addproduct')

    return render(request, 'admin_log/add_product.html', {'form': form, 'brand_form': brand_form})


@admin_required
def product_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Product updated successfully.')
                return redirect('product_det:product_details')
            except Exception:
                logger.exception("Error updating product %s", pk)
                messages.error(request, "Failed to update product.")
        else:
            for error in form.errors.values():
                messages.error(request, error.as_text())
    else:
        form = ProductForm(instance=product)

    return render(request, 'admin_log/product_update.html', {'form': form, 'product': product})


@admin_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        try:
            product.soft_delete()
            messages.success(request, f'Product "{product.title}" deleted.')
        except Exception:
            logger.exception("Error deleting product %s", pk)
            messages.error(request, "Failed to delete product.")
        return redirect('product_det:product_details')

    return render(request, 'admin_log/product_delete.html', {'product': product})


@admin_required
def brand_update(request, id):
    brand = get_object_or_404(Brand, id=id)
    if request.method == 'POST':
        form = BrandForm(request.POST, instance=brand)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Brand updated successfully.')
                return redirect('product_det:product_details')
            except Exception:
                logger.exception("Error updating brand %s", id)
                messages.error(request, "Failed to update brand.")
        else:
            for error in form.errors.values():
                messages.error(request, error.as_text())
    else:
        form = BrandForm(instance=brand)

    return render(request, 'admin_log/edit_brand.html', {'brand': brand, 'form': form})


@admin_required
def brand_delete(request, id):
    brand = get_object_or_404(Brand, id=id)
    if request.method == 'POST':
        try:
            brand.soft_delete()
            messages.success(request, f'Brand "{brand.name}" deleted.')
        except Exception:
            logger.exception("Error deleting brand %s", id)
            messages.error(request, "Failed to delete brand.")
        return redirect('product_det:product_details')

    return render(request, 'admin_log/delete_brand.html', {'brand': brand})


# ─── Variants ─────────────────────────────────────────────────────────────────

@admin_required
def add_variants(request):
    variant_form = ProductVariantForm()
    color_form = ColorForm()

    if request.method == 'POST':
        if 'add_variant' in request.POST:
            variant_form = ProductVariantForm(request.POST, request.FILES)
            if variant_form.is_valid():
                try:
                    variant_form.save()
                    messages.success(request, 'Variant added successfully.', extra_tags='variant')
                    return redirect('product_det:variant_details')
                except Exception:
                    logger.exception("Error adding variant")
                    messages.error(request, "Failed to add variant.", extra_tags='variant')
            else:
                messages.error(request, "Invalid variant data.", extra_tags='variant')

        elif 'add_color' in request.POST:
            color_form = ColorForm(request.POST)
            if color_form.is_valid():
                try:
                    color_form.save()
                    messages.success(request, 'Color added successfully.', extra_tags='color')
                    return redirect('product_det:add_variants')
                except Exception:
                    logger.exception("Error adding color")
                    messages.error(request, "Failed to add color.", extra_tags='color')
            else:
                messages.error(request, "Invalid color data.", extra_tags='color')

    return render(request, 'admin_log/add_variants.html', {
        'variant_form': variant_form,
        'color_form': color_form,
    })


@admin_required
@require_GET
def filter_products(request):
    brand_id = request.GET.get('brand_id')
    if brand_id:
        try:
            products = Product.objects.filter(
                brand_id=int(brand_id), deleted=False
            ).values('id', 'title')
            return JsonResponse(list(products), safe=False)
        except (ValueError, TypeError):
            logger.warning("Invalid brand_id in filter_products: %s", brand_id)
    return JsonResponse([], safe=False)


@admin_required
def variant_details(request):
    variants_qs = ProductVariant.objects.filter(
        deleted=False
    ).select_related('product__category', 'product__brand', 'color')

    paginator = Paginator(variants_qs, 10)
    page = request.GET.get('page')
    try:
        variants = paginator.page(page)
    except (EmptyPage, PageNotAnInteger):
        variants = paginator.page(1)

    return render(request, 'admin_log/variant_details.html', {'variants': variants})


@admin_required
def edit_variant(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)

    if request.method == 'POST':
        form = ProductVariantForm(request.POST, request.FILES, instance=variant)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Variant updated successfully.', extra_tags='variant')
                return redirect('product_det:variant_details')
            except ValidationError as e:
                messages.error(request, str(e), extra_tags='variant')
            except IntegrityError:
                messages.error(request, "A variant with this combination already exists.", extra_tags='variant')
            except Exception:
                logger.exception("Error updating variant %s", variant_id)
                messages.error(request, "Failed to update variant.", extra_tags='variant')
        else:
            messages.error(request, "Invalid variant data.", extra_tags='variant')
    else:
        form = ProductVariantForm(instance=variant)

    return render(request, 'admin_log/edit_variant.html', {'variant_form': form, 'variant': variant})


@admin_required
def delete_variant(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    if request.method == 'POST':
        try:
            variant.soft_delete()
            messages.success(request, 'Variant deleted successfully.', extra_tags='variant')
        except Exception:
            logger.exception("Error deleting variant %s", variant_id)
            messages.error(request, "Failed to delete variant.", extra_tags='variant')
        return redirect('product_det:variant_details')

    return render(request, 'admin_log/delete_variant.html', {'variant': variant})