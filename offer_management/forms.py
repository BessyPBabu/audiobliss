from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Offer, ProductOffer, CategoryOffer
from product_management.models import Product, Category


class OfferForm(forms.ModelForm):
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(deleted=False, is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.filter(is_deleted=False, is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
    )

    class Meta:
        model = Offer
        fields = ['name', 'description', 'offer_type', 'discount_percentage',
                  'start_date', 'end_date', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'offer_type': forms.Select(attrs={'class': 'form-control'}),
            'discount_percentage': forms.NumberInput(attrs={'class': 'form-control'}),
            'start_date': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'}
            ),
            'end_date': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'}
            ),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if len(name) < 3:
            raise ValidationError("Offer name must be at least 3 characters.")
        return name

    def clean_discount_percentage(self):
        discount = self.cleaned_data.get('discount_percentage')
        if discount is not None and not (0 < discount <= 100):
            raise ValidationError("Discount percentage must be between 1 and 100.")
        return discount

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        offer_type = cleaned_data.get('offer_type')

        if start_date and end_date:
            if start_date >= end_date:
                raise ValidationError("End date must be after start date.")

        if offer_type == 'product' and not cleaned_data.get('product'):
            raise ValidationError("A product must be selected for product offers.")
        if offer_type == 'category' and not cleaned_data.get('category'):
            raise ValidationError("A category must be selected for category offers.")

        return cleaned_data


class ProductOfferForm(forms.ModelForm):
    class Meta:
        model = ProductOffer
        fields = ['offer', 'product']
        widgets = {
            'offer': forms.Select(attrs={'class': 'form-control'}),
            'product': forms.Select(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        offer = cleaned_data.get('offer')
        product = cleaned_data.get('product')
        if offer and product:
            existing = ProductOffer.objects.filter(
                product=product, offer__end_date__gt=timezone.now()
            ).exclude(pk=self.instance.pk).first()
            if existing:
                raise ValidationError(
                    f"This product already has an active offer: {existing.offer.name}"
                )
        return cleaned_data


class CategoryOfferForm(forms.ModelForm):
    class Meta:
        model = CategoryOffer
        fields = ['offer', 'category']
        widgets = {
            'offer': forms.Select(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        offer = cleaned_data.get('offer')
        category = cleaned_data.get('category')
        if offer and category:
            existing = CategoryOffer.objects.filter(
                category=category, offer__end_date__gt=timezone.now()
            ).exclude(pk=self.instance.pk).first()
            if existing:
                raise ValidationError(
                    f"This category already has an active offer: {existing.offer.name}"
                )
        return cleaned_data
