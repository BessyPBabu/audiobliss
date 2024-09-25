from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Offer, ProductOffer, CategoryOffer, ReferralOffer
from .forms import OfferForm, ProductOfferForm, CategoryOfferForm



# Create your views here.

@login_required
def offer_list(request):
    offers = Offer.objects.all()
    context = {
        'offers': offers,
    }
    return render(request, 'admin_log/offer_list.html', context)

@login_required
def offer_detail(request, pk):
    offer = get_object_or_404(Offer, pk=pk)
    product_offers = ProductOffer.objects.filter(offer=offer)
    category_offers = CategoryOffer.objects.filter(offer=offer)
    # referral_offers = ReferralOffer.objects.filter(offer=offer)
    context = {
        'offer': offer,
        'product_offers': product_offers,
        'category_offers': category_offers,
        # 'referral_offers': referral_offers,
    }
    return render(request, 'admin_log/offer_detail.html', context)



@login_required
def offer_create(request):
    if request.method == 'POST':
        form = OfferForm(request.POST)
        if form.is_valid():
            offer = form.save()
            offer_type = form.cleaned_data['offer_type']

            if offer_type == 'product':
                ProductOffer.objects.create(offer=offer, product=form.cleaned_data['product'])
            elif offer_type == 'category':
                CategoryOffer.objects.create(offer=offer, category=form.cleaned_data['category'])
            # elif offer_type == 'referral':
            #     ReferralOffer.objects.create(offer=offer, referrer=form.cleaned_data['referrer'], referred=form.cleaned_data['referred'])

            messages.success(request, 'Offer created successfully.', extra_tags='offer_create')
            return redirect('offer_management:offer_detail', pk=offer.pk)
    else:
        form = OfferForm()
    
    context = {
        'form': form,
    }
    return render(request, 'admin_log/offer_form.html', context)

@login_required
def offer_update(request, pk):
    offer = get_object_or_404(Offer, pk=pk)
    if request.method == 'POST':
        form = OfferForm(request.POST, instance=offer)
        if form.is_valid():
            form.save()
            messages.success(request, 'Offer updated successfully.', extra_tags='offer_update')
            return redirect('offer_management:offer_detail', pk=offer.pk)
    else:
        form = OfferForm(instance=offer)
    
    context = {
        'form': form,
        'offer': offer,
    }
    return render(request, 'admin_log/offer_form.html', context)

@login_required
def offer_delete(request, pk):
    offer = get_object_or_404(Offer, pk=pk)
    if request.method == 'POST':
        offer.delete()
        messages.success(request, 'Offer deleted successfully.', extra_tags='offer_delete')
        return redirect('offer_management:offer_list')
    
    context = {
        'offer': offer,
    }
    return render(request, 'admin_log/offer_confirm_delete.html', context)

@login_required
def product_offer_create(request):
    if request.method == 'POST':
        form = ProductOfferForm(request.POST)
        if form.is_valid():
            product_offer = form.save()
            messages.success(request, 'Product offer created successfully.', extra_tags='product_offer_create')
            return redirect('offer_management:offer_detail', pk=product_offer.offer.pk)
    else:
        form = ProductOfferForm()
    
    context = {
        'form': form,
    }
    return render(request, 'admin_log//product_offer_form.html', context)

@login_required
def category_offer_create(request):
    if request.method == 'POST':
        form = CategoryOfferForm(request.POST)
        if form.is_valid():
            category_offer = form.save()
            messages.success(request, 'Category offer created successfully.', extra_tags='category_offer_create')
            return redirect('offer_management:offer_detail', pk=category_offer.offer.pk)
    else:
        form = CategoryOfferForm()
    
    context = {
        'form': form,
    }
    return render(request, 'admin_log/category_offer_form.html', context)

# @login_required
# def referral_offer_create(request):
#     if request.method == 'POST':
#         form = ReferralOfferForm(request.POST)
#         if form.is_valid():
#             referral_offer = form.save()
#             messages.success(request, 'Referral offer created successfully.', extra_tags='referral_offer_create')
#             return redirect('offer_management:offer_detail', pk=referral_offer.offer.pk)
#     else:
#         form = ReferralOfferForm()
    
#     context = {
#         'form': form,
#     }
#     return render(request, 'admin_log/referral_offer_form.html', context)