import logging
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from .forms import OfferForm, ProductOfferForm, CategoryOfferForm
from .models import Offer, ProductOffer, CategoryOffer

logger = logging.getLogger(__name__)


@login_required
def offer_list(request):
    offers = Offer.objects.all().order_by('-id')
    return render(request, 'admin_log/offer_list.html', {'offers': offers})


@login_required
def offer_detail(request, pk):
    offer = get_object_or_404(Offer, pk=pk)
    return render(request, 'admin_log/offer_detail.html', {
        'offer': offer,
        'product_offers': offer.product_offers.select_related('product'),
        'category_offers': offer.category_offers.select_related('category'),
    })


@login_required
def offer_create(request):
    if request.method == 'POST':
        form = OfferForm(request.POST)
        if form.is_valid():
            try:
                offer = form.save()
                offer_type = form.cleaned_data['offer_type']

                if offer_type == 'product':
                    ProductOffer.objects.create(
                        offer=offer, product=form.cleaned_data['product']
                    )
                elif offer_type == 'category':
                    CategoryOffer.objects.create(
                        offer=offer, category=form.cleaned_data['category']
                    )

                messages.success(request, "Offer created successfully.")
                return redirect('offer_management:offer_detail', pk=offer.pk)
            except Exception:
                logger.exception("Error creating offer")
                messages.error(request, "Failed to create offer.")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = OfferForm()

    return render(request, 'admin_log/offer_form.html', {'form': form})


@login_required
def offer_update(request, pk):
    offer = get_object_or_404(Offer, pk=pk)
    if request.method == 'POST':
        form = OfferForm(request.POST, instance=offer)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Offer updated successfully.")
                return redirect('offer_management:offer_detail', pk=offer.pk)
            except Exception:
                logger.exception("Error updating offer %s", pk)
                messages.error(request, "Failed to update offer.")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = OfferForm(instance=offer)

    return render(request, 'admin_log/offer_form.html', {'form': form, 'offer': offer})


@login_required
def offer_delete(request, pk):
    offer = get_object_or_404(Offer, pk=pk)
    if request.method == 'POST':
        try:
            offer.delete()
            messages.success(request, "Offer deleted successfully.")
        except Exception:
            logger.exception("Error deleting offer %s", pk)
            messages.error(request, "Failed to delete offer.")
        return redirect('offer_management:offer_list')

    return render(request, 'admin_log/offer_confirm_delete.html', {'offer': offer})


@login_required
def product_offer_create(request):
    if request.method == 'POST':
        form = ProductOfferForm(request.POST)
        if form.is_valid():
            try:
                product_offer = form.save()
                messages.success(request, "Product offer created.")
                return redirect('offer_management:offer_detail', pk=product_offer.offer.pk)
            except Exception:
                logger.exception("Error creating product offer")
                messages.error(request, "Failed to create product offer.")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ProductOfferForm()

    return render(request, 'admin_log/product_offer_form.html', {'form': form})


@login_required
def category_offer_create(request):
    if request.method == 'POST':
        form = CategoryOfferForm(request.POST)
        if form.is_valid():
            try:
                category_offer = form.save()
                messages.success(request, "Category offer created.")
                return redirect('offer_management:offer_detail', pk=category_offer.offer.pk)
            except Exception:
                logger.exception("Error creating category offer")
                messages.error(request, "Failed to create category offer.")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CategoryOfferForm()

    return render(request, 'admin_log/category_offer_form.html', {'form': form})
