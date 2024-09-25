from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Offer, ProductOffer, CategoryOffer, ReferralOffer
from product_management.models import Product,Category
from user_log.models import Account

class OfferForm(forms.ModelForm):
    product = forms.ModelChoiceField(queryset=Product.objects.all(), required=False)
    category = forms.ModelChoiceField(queryset=Category.objects.all(), required=False)
    # referrer = forms.ModelChoiceField(queryset=Account.objects.all(), required=False)
    # referred = forms.ModelChoiceField(queryset=Account.objects.all(), required=False)

    class Meta:
        model = Offer
        fields = ['name', 'description', 'offer_type', 'discount_percentage', 'start_date', 'end_date', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),  # Text input for name
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),  # Textarea for description
            'offer_type': forms.Select(attrs={'class': 'form-control'}),  # Dropdown for offer_type
            'discount_percentage': forms.NumberInput(attrs={'class': 'form-control'}),  # Number input for discount
            'start_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),  # DateTime input for start date
            'end_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),  # DateTime input for end date
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if len(name) < 3:
            raise ValidationError("Name must be at least 3 characters long.")
        return name

    def clean_discount_percentage(self):
        discount = self.cleaned_data.get('discount_percentage')
        if discount <= 0 or discount > 100:
            raise ValidationError("Discount percentage must be between 0 and 100.")
        return discount
    
    def clean(self):
        cleaned_data = super().clean()
        offer_type = cleaned_data.get('offer_type')

        if offer_type == 'product' and not cleaned_data.get('product'):
            raise ValidationError("Product is required for product offers.")
        elif offer_type == 'category' and not cleaned_data.get('category'):
            raise ValidationError("Category is required for category offers.")
        elif offer_type == 'referral' and (not cleaned_data.get('referrer') or not cleaned_data.get('referred')):
            raise ValidationError("Referrer and referred are required for referral offers.")

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date:
            if start_date >= end_date:
                raise ValidationError("End date must be after start date.")

            if start_date < timezone.now():
                raise ValidationError("Start date cannot be in the past.")

        return cleaned_data
    
    
    
class ProductOfferForm(forms.ModelForm):
    class Meta:
        model = ProductOffer
        fields = ['offer', 'product']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),  # Dropdown for product field
        }

    def clean(self):
        cleaned_data = super().clean()
        offer = cleaned_data.get('offer')
        product = cleaned_data.get('product')

        if offer and product:
            existing_offer = ProductOffer.objects.filter(product=product, offer__end_date__gt=timezone.now()).exclude(pk=self.instance.pk).first()
            if existing_offer:
                raise ValidationError(f"This product already has an active offer: {existing_offer.offer.name}")

        return cleaned_data

class CategoryOfferForm(forms.ModelForm):
    class Meta:
        model = CategoryOffer
        fields = ['offer', 'category']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-control'}),  # Dropdown for category field
        }

    def clean(self):
        cleaned_data = super().clean()
        offer = cleaned_data.get('offer')
        category = cleaned_data.get('category')

        if offer and category:
            existing_offer = CategoryOffer.objects.filter(category=category, offer__end_date__gt=timezone.now()).exclude(pk=self.instance.pk).first()
            if existing_offer:
                raise ValidationError(f"This category already has an active offer: {existing_offer.offer.name}")

        return cleaned_data

# class ReferralOfferForm(forms.ModelForm):
#     class Meta:
#         model = ReferralOffer
#         fields = ['offer', 'referrer', 'referred']

#     def clean(self):
#         cleaned_data = super().clean()
#         referrer = cleaned_data.get('referrer')
#         referred = cleaned_data.get('referred')

#         if referrer and referred:
#             if referrer == referred:
#                 raise ValidationError("Referrer and referred users cannot be the same.")

#             existing_referral = ReferralOffer.objects.filter(referrer=referrer, referred=referred, is_claimed=False).exclude(pk=self.instance.pk).first()
#             if existing_referral:
#                 raise ValidationError("An unclaimed referral offer already exists between these users.")

#         return cleaned_data