from django import forms
from django.utils import timezone
from .models import Coupon
from django.core.exceptions import ValidationError

class CouponForm(forms.ModelForm):
    class Meta:
        model = Coupon
        fields = ['code', 'discount_type', 'discount_value', 'min_purchase_amount', 'expiration_date', 'active']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'discount_type': forms.Select(attrs={'class': 'form-control'}),  # Assuming it's a dropdown (Select)
            'discount_value': forms.NumberInput(attrs={'class': 'form-control'}),
            'min_purchase_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'expiration_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),  # Checkbox uses 'form-check-input'
            'description': forms.Textarea(attrs={'class': 'form-control'})
        }

    # Custom validation to ensure min_purchase_amount is not zero or negative
    def clean_min_purchase_amount(self):
        min_purchase_amount = self.cleaned_data.get('min_purchase_amount')
        if min_purchase_amount is not None and min_purchase_amount <= 0:
            raise ValidationError('Minimum purchase amount must be greater than zero.')
        return min_purchase_amount

    def clean_expiration_date(self):
        expiration_date = self.cleaned_data.get('expiration_date')
        if expiration_date and timezone.is_naive(expiration_date):
            expiration_date = timezone.make_aware(expiration_date)
        return expiration_date

class UserCouponForm(forms.Form):
    code = forms.CharField(max_length=50, label='Coupon Code')