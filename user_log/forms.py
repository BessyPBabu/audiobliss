from django import forms
from django.contrib.auth.forms import UserCreationForm , PasswordResetForm
from .models import Account ,Address
import re
from django.core.validators import validate_email

class RegistrationForm(UserCreationForm):
    email = forms.EmailField(max_length=60, help_text="Required. Add a valid email address")

    class Meta:
        model = Account
        fields = ("email", "username", "password1", "password2")

class AccountAuthenticationForm(forms.ModelForm):
    password = forms.CharField(label='Password', widget=forms.PasswordInput)

    class Meta:
        model = Account
        fields = ('email', 'password')

    def clean(self):
        if self.is_valid():
            email = self.cleaned_data['email']
            password = self.cleaned_data['password']
            if not Account.objects.filter(email=email).exists():
                raise forms.ValidationError("Invalid login")
            user = Account.objects.get(email=email)
            if not user.check_password(password):
                raise forms.ValidationError("Invalid password")
        return self.cleaned_data
    
class OTPForm(forms.Form):
    otp = forms.CharField(label='OTP', max_length=6)




class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ['house_name', 'streat_name', 'post_office', 'place', 'district', 'state', 'country', 'pincode']
        widgets = {
            'house_name': forms.TextInput(attrs={'class': 'form-control'}),
            'streat_name': forms.TextInput(attrs={'class': 'form-control'}),
            'post_office': forms.TextInput(attrs={'class': 'form-control'}),
            'place': forms.TextInput(attrs={'class': 'form-control'}),
            'district': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'pincode': forms.TextInput(attrs={'class': 'form-control'}),
        }
        error_messages = {
            'house_name': {
                'required': 'House name is required.',
                'max_length': 'House name cannot exceed 40 characters.'
            },
            'streat_name': {
                'required': 'Street name is required.',
                'max_length': 'Street name cannot exceed 50 characters.'
            },
            'post_office': {
                'required': 'Post office is required.',
                'max_length': 'Post office cannot exceed 20 characters.'
            },
            'place': {
                'required': 'Place is required.',
                'max_length': 'Place cannot exceed 25 characters.'
            },
            'district': {
                'required': 'District is required.',
                'max_length': 'District cannot exceed 20 characters.'
            },
            'state': {
                'required': 'State is required.',
                'max_length': 'State cannot exceed 30 characters.'
            },
            'country': {
                'max_length': 'Country cannot exceed 35 characters.'
            },
            'pincode': {
                'required': 'Pincode is required.',
                'max_length': 'Pincode cannot exceed 6 characters.',
                'invalid': 'Enter a valid 6-digit pincode.'
            }
        }

    def clean_house_name(self):
        house_name = self.cleaned_data.get('house_name')
        if not re.match(r'^[a-zA-Z0-9\s]+$', house_name):
            raise forms.ValidationError('House name can only contain letters, numbers, and spaces.')
        return house_name

    def clean_streat_name(self):
        streat_name = self.cleaned_data.get('streat_name')
        if not re.match(r'^[a-zA-Z\s]+$', streat_name):
            raise forms.ValidationError('Street name can only contain letters and spaces.')
        return streat_name

    def clean_post_office(self):
        post_office = self.cleaned_data.get('post_office')
        if not re.match(r'^[a-zA-Z\s]+$', post_office):
            raise forms.ValidationError('Post office can only contain letters and spaces.')
        return post_office

    def clean_place(self):
        place = self.cleaned_data.get('place')
        if not re.match(r'^[a-zA-Z\s]+$', place):
            raise forms.ValidationError('Place can only contain letters and spaces.')
        return place

    def clean_district(self):
        district = self.cleaned_data.get('district')
        if not re.match(r'^[a-zA-Z\s]+$', district):
            raise forms.ValidationError('District can only contain letters and spaces.')
        return district

    def clean_state(self):
        state = self.cleaned_data.get('state')
        if not re.match(r'^[a-zA-Z\s]+$', state):
            raise forms.ValidationError('State can only contain letters and spaces.')
        return state

    def clean_country(self):
        country = self.cleaned_data.get('country')
        if country and not re.match(r'^[a-zA-Z\s]+$', country):
            raise forms.ValidationError('Country can only contain letters and spaces.')
        return country

    def clean_pincode(self):
        pincode = self.cleaned_data.get('pincode')
        if not pincode or not re.match(r'^\d{6}$', pincode):
            raise forms.ValidationError('Enter a valid 6-digit pincode.')
        return pincode





class CustomPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(label='Email', max_length=254, widget=forms.EmailInput(attrs={'class': 'form-control'}))

    def clean_email(self):
        email = self.cleaned_data['email']
        if not Account.objects.filter(email=email).exists():
            raise forms.ValidationError("There is no user registered with the specified email address!")
        return email
    


class AccountUpdateForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ['username', 'phone', 'profile_image']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['profile_image'].widget.attrs.update({'class': 'form-control-file'})

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise forms.ValidationError('Username can only contain letters, numbers, and underscores.')
        return username

    # def clean_email(self):
    #     email = self.cleaned_data.get('email')
    #     validate_email(email)  # Use Django's built-in email validator
    #     return email

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if not re.match(r'^\+?\d{10,15}$', phone):
            raise forms.ValidationError('Enter a valid phone number with 10-15 digits.')
        return phone


class EmailUpdateForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ['new_email']

    def clean_new_email(self):
        new_email = self.cleaned_data.get('new_email')
        if Account.objects.filter(email=new_email).exists():
            raise forms.ValidationError("This email is already in use.")
        return new_email