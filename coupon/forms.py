from django import forms
from django.utils import timezone
from .models import Coupon


class CouponForm(forms.ModelForm):
    class Meta:
        model = Coupon
        fields = ['code', 'discount_type', 'discount_value', 'min_purchase_amount',
                  'expiration_date', 'active', 'description']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'discount_type': forms.Select(attrs={'class': 'form-control'}),
            'discount_value': forms.NumberInput(attrs={'class': 'form-control'}),
            'min_purchase_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'expiration_date': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'}
            ),
            'active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean_discount_value(self):
        value = self.cleaned_data.get('discount_value')
        if value is not None and value <= 0:
            raise forms.ValidationError("Discount value must be greater than zero.")
        return value

    def clean_min_purchase_amount(self):
        amount = self.cleaned_data.get('min_purchase_amount')
        if amount is not None and amount <= 0:
            raise forms.ValidationError("Minimum purchase amount must be greater than zero.")
        return amount

    def clean_expiration_date(self):
        expiration_date = self.cleaned_data.get('expiration_date')
        if expiration_date:
            if timezone.is_naive(expiration_date):
                expiration_date = timezone.make_aware(expiration_date)
        return expiration_date


class UserCouponForm(forms.Form):
    code = forms.CharField(
        max_length=20,
        label='Coupon Code',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter coupon code'}),
    )

    def clean_code(self):
        return self.cleaned_data.get('code', '').strip().upper()
