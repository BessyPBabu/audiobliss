from django import forms
from .models import Order, Payment


# PaymentForm
class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['payment_id', 'payment_method']
        widgets = {
            'payment_id': forms.TextInput(attrs={'class': 'form-control'}),
            'payment_method': forms.TextInput(attrs={'class': 'form-control'}),
        }
        error_messages = {
            'payment_id': {
                'required': 'Payment ID is required.',
                'max_length': 'Payment ID cannot exceed 100 characters.'
            },
            'payment_method': {
                'required': 'Payment method is required.',
                'max_length': 'Payment method cannot exceed 100 characters.'
            }
        }

    def clean_payment_id(self):
        payment_id = self.cleaned_data.get('payment_id')
        if not payment_id:
            raise forms.ValidationError('Payment ID is required.')
        return payment_id

    def clean_payment_method(self):
        payment_method = self.cleaned_data.get('payment_method')
        if not payment_method:
            raise forms.ValidationError('Payment method is required.')
        return payment_method


# OrderForm
class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['order_note', 'status', 'order_total', 'tax']
        widgets = {
            'order_note': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'order_total': forms.NumberInput(attrs={'class': 'form-control'}),
            'tax': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        error_messages = {
            'order_note': {
                'max_length': 'Order note cannot exceed 100 characters.'
            },
            'status': {
                'required': 'Order status is required.',
                'max_length': 'Status cannot exceed 10 characters.'
            },
            'order_total': {
                'required': 'Order total is required.',
            },
            'tax': {
                'required': 'Tax is required.',
            }
        }

    def __init__(self, *args, **kwargs):
        super(OrderForm, self).__init__(*args, **kwargs)
        # Make the order_total field read-only
        self.fields['order_total'].widget.attrs['readonly'] = True


    def clean_order_note(self):
        order_note = self.cleaned_data.get('order_note')
        if order_note and len(order_note) > 100:
            raise forms.ValidationError('Order note cannot exceed 100 characters.')
        return order_note


CANCEL_REASON_CHOICES = [
    ('Changed my mind', 'Changed my mind'),
    ('Ordered by mistake', 'Ordered by mistake'),
    ('Found a better price', 'Found a better price'),
    ('others', 'others'),
]

class CancelOrderForm(forms.Form):
    reason = forms.ChoiceField(choices=CANCEL_REASON_CHOICES, required=False, label="Select a reason")
    custom_reason = forms.CharField(max_length=255, required=False, label="Or provide a custom reason")
    
    def clean(self):
        cleaned_data = super().clean()
        reason = cleaned_data.get('reason')
        custom_reason = cleaned_data.get('custom_reason')
        
        if not reason and not custom_reason:
            raise forms.ValidationError("Please select or provide a reason for cancellation.")
        return cleaned_data


from django import forms
from .models import ReturnRequest

class ReturnRequestForm(forms.ModelForm):
    class Meta:
        model = ReturnRequest
        fields = ['reason']
        widgets = {
            'reason': forms.Textarea(attrs={'rows': 4, 'cols': 50})
        }
