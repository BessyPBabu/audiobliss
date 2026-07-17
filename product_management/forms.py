import re
from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from .models import Category, Product, ProductVariant, Color, Brand


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Category name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Description', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not re.match(r'^[a-zA-Z0-9\s]{2,50}$', name):
            raise forms.ValidationError(
                "Category name must be 2-50 characters: letters, numbers, spaces only."
            )
        if Category.objects.filter(name__iexact=name).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("A category with this name already exists.")
        return name


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['title', 'description', 'brand', 'category', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Product title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'brand': forms.Select(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['brand'].queryset = Brand.objects.filter(is_active=True, is_deleted=False)
        self.fields['category'].queryset = Category.objects.filter(is_active=True, is_deleted=False)

    def clean_title(self):
        title = self.cleaned_data.get('title', '').strip()
        if not re.match(r'^[a-zA-Z0-9\s]{3,100}$', title):
            raise forms.ValidationError(
                "Title must be 3-100 characters: letters, numbers, spaces only."
            )
        if Product.objects.filter(title__iexact=title, deleted=False).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("A product with this title already exists.")
        return title

    def clean(self):
        cleaned_data = super().clean()
        brand = cleaned_data.get('brand')
        category = cleaned_data.get('category')
        if brand and not brand.is_active:
            raise forms.ValidationError("Selected brand is not active.")
        if category and not category.is_active:
            raise forms.ValidationError("Selected category is not active.")
        return cleaned_data


class ProductVariantForm(forms.ModelForm):
    class Meta:
        model = ProductVariant
        fields = ['product', 'color', 'price', 'stock', 'max_quantity_per_user',
                  'image1', 'image2', 'image3', 'is_active']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'color': forms.Select(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'max_quantity_per_user': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is not None and price < 0:
            raise forms.ValidationError("Price must be non-negative.")
        return price

    def clean_stock(self):
        stock = self.cleaned_data.get('stock')
        if stock is not None and stock < 0:
            raise forms.ValidationError("Stock must be non-negative.")
        return stock

    def clean_max_quantity_per_user(self):
        qty = self.cleaned_data.get('max_quantity_per_user')
        if qty is not None and qty < 1:
            raise forms.ValidationError("Max quantity per user must be at least 1.")
        return qty

    
    ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp'}

    def _clean_image(self, field_name):
        image = self.cleaned_data.get(field_name)
        if not image:
            return image

        if hasattr(image, 'size') and image.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Image file too large (max 5MB).")

        if getattr(image, 'content_type', None) not in self.ALLOWED_IMAGE_TYPES:
            raise forms.ValidationError("Only JPEG, PNG or WEBP images are allowed.")

        try:
            from PIL import Image
            image.seek(0)
            Image.open(image).verify()
            image.seek(0)
        except Exception:
            raise forms.ValidationError("Uploaded file is not a valid image.")

        return image

    def clean_image1(self):
        return self._clean_image('image1')

    def clean_image2(self):
        return self._clean_image('image2')

    def clean_image3(self):
        return self._clean_image('image3')


class ColorForm(forms.ModelForm):
    class Meta:
        model = Color
        fields = ['name', 'hex_code']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Color name'}),
            'hex_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '#FF0000'}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not re.match(r'^[a-zA-Z\s]{2,30}$', name):
            raise forms.ValidationError("Color name must be 2-30 characters, letters and spaces only.")
        return name

    def clean_hex_code(self):
        hex_code = self.cleaned_data.get('hex_code', '').strip()
        if hex_code and not re.match(r'^#[0-9A-Fa-f]{6}$', hex_code):
            raise forms.ValidationError("Enter a valid hex color code (e.g., #FF0000).")
        return hex_code


class BrandForm(forms.ModelForm):
    class Meta:
        model = Brand
        fields = ['name', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Brand name'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not re.match(r'^[A-Za-z]+(?: [A-Za-z]+)*$', name):
            raise forms.ValidationError(
                "Brand name must contain only letters with single spaces between words."
            )
        if Brand.objects.filter(name__iexact=name).exclude(pk=self.instance.pk).exists():
            raise ValidationError("A brand with this name already exists.")
        return name
