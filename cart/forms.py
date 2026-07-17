from django import forms


class AddToCartForm(forms.Form):
    product_variant_id = forms.IntegerField(min_value=1)
    quantity = forms.IntegerField(min_value=1, max_value=100, initial=1)