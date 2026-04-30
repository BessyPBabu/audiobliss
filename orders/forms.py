from django import forms
from .models import Order, Payment, ReturnRequest

CANCEL_REASON_CHOICES = [
    ('Changed my mind', 'Changed my mind'),
    ('Ordered by mistake', 'Ordered by mistake'),
    ('Found a better price', 'Found a better price'),
    ('Others', 'Others'),
]


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['order_note', 'status', 'order_total', 'tax']
        widgets = {
            'order_note': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'order_total': forms.NumberInput(attrs={'class': 'form-control', 'readonly': True}),
            'tax': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def clean_order_note(self):
        note = self.cleaned_data.get('order_note', '')
        if len(note) > 100:
            raise forms.ValidationError("Order note cannot exceed 100 characters.")
        return note


class CancelOrderForm(forms.Form):
    reason = forms.ChoiceField(
        choices=CANCEL_REASON_CHOICES,
        required=False,
        label="Select a reason",
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    custom_reason = forms.CharField(
        max_length=255,
        required=False,
        label="Or provide a custom reason",
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )

    def clean(self):
        cleaned_data = super().clean()
        reason = cleaned_data.get('reason')
        custom_reason = cleaned_data.get('custom_reason', '').strip()
        if not reason and not custom_reason:
            raise forms.ValidationError("Please select or provide a reason for cancellation.")
        return cleaned_data


class ReturnRequestForm(forms.ModelForm):
    class Meta:
        model = ReturnRequest
        fields = ['reason']
        widgets = {
            'reason': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        }
