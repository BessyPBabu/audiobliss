import re
from django import forms
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from .models import Category, Product, ProductVariant, Color,Brand

class CategoryForm(forms.ModelForm):
    name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Category name'}),
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z0-9\s]{2,50}$',
                message="Category name must be 2-50 characters long and can only contain letters, numbers, and spaces."
            )
        ]
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Category description'}),
        validators=[
            RegexValidator(
                regex=r'^[\w\s.,!?-]{10,500}$',
                message="Description must be 10-500 characters long and can contain letters, numbers, spaces, and basic punctuation."
            )
        ]
    )
    

    is_active = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        initial=True,
        label="Active"
    )

    class Meta:
        model = Category
        fields = ['name', 'description', 'is_active']

    def clean_name(self):
        name = self.cleaned_data['name']
        if Category.objects.filter(name__iexact=name).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("A category with this name already exists.")
        return name

class ProductForm(forms.ModelForm):
    title = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter product title'}),
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z0-9\s]{3,100}$',
                message="Title must be 3-100 characters long and can only contain letters, numbers, and spaces."
            )
        ]
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter product description', 'rows': 4}),
        validators=[
            RegexValidator(
                regex=r'^[\w\s.,!?-]{10,1000}$',
                message="Description must be 10-1000 characters long and can contain letters, numbers, spaces, and basic punctuation."
            )
        ]
    )
    brand = forms.ModelChoiceField(
        queryset=Brand.objects.filter(is_active=True),
        empty_label="Select Brand",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.filter(is_active=True),
        empty_label="Select Category",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    is_active = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        initial=True,
        label="Active"
    )

    class Meta:
        model = Product
        fields = ['title', 'description', 'brand', 'category', 'is_active']

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.get('instance')
        super().__init__(*args, **kwargs)

    def clean_title(self):
        title = self.cleaned_data.get('title')
        if Product.objects.filter(title__iexact=title).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Product with this title already exists.")
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
    brand = forms.ModelChoiceField(
        queryset=Brand.objects.all(),
        empty_label="Select a brand",
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False
    )
    
    
    color = forms.ModelChoiceField(
        queryset=Color.objects.all(), 
        empty_label="Select a color",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    price = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter price'}),
        validators=[
            RegexValidator(
                regex=r'^\d+(\.\d{1,2})?$',
                message="Price must be a valid number with up to two decimal places and non-negative."
            )
        ]
    )
    stock = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter stock quantity'}),
        validators=[
            RegexValidator(
                regex=r'^\d+$',
                message="Stock must be a non-negative integer."
            )
        ]
    )
    max_quantity_per_user = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter max quantity per user'}),
        validators=[
            RegexValidator(
                regex=r'^\d+$',
                message="Max quantity per user must be a non-negative integer."
            )
        ]
    )
    is_active = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        initial=True,
        label="Active"
    )
    image1 = forms.ImageField(
        widget=forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
        required=False
    )
    image2 = forms.ImageField(
        widget=forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
        required=False
    )
    image3 = forms.ImageField(
        widget=forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
        required=False
    )


    class Meta:
        model = ProductVariant
        fields = ['brand','product', 'color', 'price', 'stock', 'max_quantity_per_user', 'image1', 'image2', 'image3', 'is_active']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
        }

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price < 0:
            raise forms.ValidationError("Price must be non-negative.")
        return price

    def clean_stock(self):
        stock = self.cleaned_data.get('stock')
        if stock < 0:
            raise forms.ValidationError("Stock must be non-negative.")
        return stock

    def clean_max_quantity_per_user(self):
        max_quantity_per_user = self.cleaned_data.get('max_quantity_per_user')
        if max_quantity_per_user < 0:
            raise forms.ValidationError("Max quantity per user must be non-negative.")
        return max_quantity_per_user
    
    def clean_image1(self):
        image1 = self.cleaned_data.get('image1')
        if image1 and image1.size > 5 * 1024 * 1024:  # 5MB limit
            raise forms.ValidationError("Image file too large ( > 5mb )")
        return image1

    def clean_image2(self):
        image2 = self.cleaned_data.get('image2')
        if image2 and image2.size > 5 * 1024 * 1024:  # 5MB limit
            raise forms.ValidationError("Image file too large ( > 5mb )")
        return image2

    def clean_image3(self):
        image3 = self.cleaned_data.get('image3')
        if image3 and image3.size > 5 * 1024 * 1024:  # 5MB limit
            raise forms.ValidationError("Image file too large ( > 5mb )")
        return image3
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'brand' in self.data:
            try:
                brand_id = int(self.data.get('brand'))
                self.fields['product'].queryset = Product.objects.filter(brand_id=brand_id).order_by('title')
            except (ValueError, TypeError):
                pass
        elif self.instance.pk:
            self.fields['product'].queryset = self.instance.product.brand.product_set.order_by('title')

class ColorForm(forms.ModelForm):
    name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter color name'}),
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z\s]{2,30}$',
                message="Color name must be 2-30 characters long and can only contain letters and spaces."
            )
        ]
    )
    hex_code = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter hex code (e.g., #FF0000)'}),
        validators=[
            RegexValidator(
                regex=r'^#[0-9A-Fa-f]{6}$',
                message="Enter a valid hex color code (e.g., #FF0000)."
            )
        ]
    )

    class Meta:
        model = Color
        fields = ['name', 'hex_code']

class BrandForm(forms.ModelForm):
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter brand name'}),
        validators=[
            RegexValidator(
                regex=r'^[A-Za-z]+(?: [A-Za-z]+)*$', 
                message="Brand name must contain only letters and no numbers, special characters, or extra spaces."
            )
        ]
    )

    is_active = forms.BooleanField(
        required=False,  # Make this optional
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = Brand
        fields = ['name', 'is_active']

    def clean_name(self):
        name = self.cleaned_data.get('name').strip()
        # Exclude the current instance from the duplication check
        if self.instance and self.instance.pk:
            if Brand.objects.filter(name__iexact=name).exclude(pk=self.instance.pk).exists():
                raise ValidationError("A brand with this name already exists.")
        else:
            if Brand.objects.filter(name__iexact=name).exists():
                raise ValidationError("A brand with this name already exists.")
        return name
