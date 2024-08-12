import re
from django import forms
from django.core.validators import RegexValidator
from .models import Category, Product, ProductVariant, Color

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
    

    class Meta:
        model = Category
        fields = ['name', 'description']

    def clean_name(self):
        name = self.cleaned_data['name']
        if Category.objects.filter(name__iexact=name).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("A category with this name already exists.")
        return name

class ProductForm(forms.ModelForm):
    title = forms.CharField(
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z0-9\s]{3,100}$',
                message="Title must be 3-100 characters long and can only contain letters, numbers, and spaces."
            )
        ]
    )
    description = forms.CharField(
        widget=forms.Textarea,
        validators=[
            RegexValidator(
                regex=r'^[\w\s.,!?-]{10,1000}$',
                message="Description must be 10-1000 characters long and can contain letters, numbers, spaces, and basic punctuation."
            )
        ]
    )
    brand_name = forms.ChoiceField(choices=[('boAt', 'boAt'), ('Noise', 'Noise'), ('Boult Audio', 'Boult Audio'), ('JBL', 'JBL'), ('Zebronics', 'Zebronics')])
  
    category = forms.ModelChoiceField(queryset=Category.objects.all(), empty_label="Select Category")

    class Meta:
        model = Product
        fields = ['title', 'description', 'brand_name',  'category']

    
    def clean_title(self):
        title = self.cleaned_data.get('title')
        if Product.objects.filter(title__iexact=title).exists():
            raise forms.ValidationError("Product with this title already exists.")
        return title

    




class ProductVariantForm(forms.ModelForm):
    color = forms.ModelChoiceField(queryset=Color.objects.all(), empty_label="Select a color")
    price = forms.DecimalField(
        validators=[
            RegexValidator(
                regex=r'^\d+(\.\d{1,2})?$',
                message="Price must be a valid number with up to two decimal places and non-negative."
            )
        ]
    )
    stock = forms.IntegerField(
        validators=[
            RegexValidator(
                regex=r'^\d+$',
                message="Stock must be a non-negative integer."
            )
        ]
    )
    max_quantity_per_user = forms.IntegerField(
        validators=[
            RegexValidator(
                regex=r'^\d+$',
                message="Max quantity per user must be a non-negative integer."
            )
        ]
    )

    class Meta:
        model = ProductVariant
        fields = ['product', 'color', 'price', 'stock', 'max_quantity_per_user', 'image1', 'image2', 'image3']

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
    



class ColorForm(forms.ModelForm):
    name = forms.CharField(
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z\s]{2,30}$',
                message="Color name must be 2-30 characters long and can only contain letters and spaces."
            )
        ]
    )
    hex_code = forms.CharField(
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


