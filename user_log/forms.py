import re
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Account, Address


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(max_length=60)

    class Meta:
        model = Account
        fields = ('email', 'username', 'password1', 'password2')

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if not re.match(r'^[a-zA-Z0-9_]{3,30}$', username):
            raise forms.ValidationError(
                "Username must be 3-30 characters: letters, numbers, underscores only."
            )
        return username


class AccountAuthenticationForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)


class OTPForm(forms.Form):
    otp = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={'placeholder': 'Enter 6-digit OTP'}),
    )

    def clean_otp(self):
        otp = self.cleaned_data.get('otp', '')
        if not otp.isdigit():
            raise forms.ValidationError("OTP must contain digits only.")
        return otp


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = [
            'house_name', 'streat_name', 'post_office', 'place',
            'district', 'state', 'country', 'pincode',
        ]
        widgets = {
            field: forms.TextInput(attrs={'class': 'form-control'})
            for field in [
                'house_name', 'streat_name', 'post_office', 'place',
                'district', 'state', 'country', 'pincode',
            ]
        }

    def _validate_alpha_field(self, field_name, label):
        value = self.cleaned_data.get(field_name, '').strip()
        if not re.match(r'^[a-zA-Z\s]+$', value):
            raise forms.ValidationError(f"{label} can only contain letters and spaces.")
        return value

    def clean_house_name(self):
        value = self.cleaned_data.get('house_name', '').strip()
        if not re.match(r'^[a-zA-Z0-9\s]+$', value):
            raise forms.ValidationError("House name can only contain letters, numbers, and spaces.")
        return value

    def clean_streat_name(self):
        return self._validate_alpha_field('streat_name', 'Street name')

    def clean_post_office(self):
        return self._validate_alpha_field('post_office', 'Post office')

    def clean_place(self):
        return self._validate_alpha_field('place', 'Place')

    def clean_district(self):
        return self._validate_alpha_field('district', 'District')

    def clean_state(self):
        return self._validate_alpha_field('state', 'State')

    def clean_country(self):
        country = self.cleaned_data.get('country', '').strip()
        if country and not re.match(r'^[a-zA-Z\s]+$', country):
            raise forms.ValidationError("Country can only contain letters and spaces.")
        return country

    def clean_pincode(self):
        pincode = self.cleaned_data.get('pincode', '').strip()
        if not re.match(r'^\d{6}$', pincode):
            raise forms.ValidationError("Enter a valid 6-digit pincode.")
        return pincode


class AccountUpdateForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ['username', 'phone', 'profile_image']

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise forms.ValidationError(
                "Username can only contain letters, numbers, and underscores."
            )
        return username

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if phone and not re.match(r'^\+?\d{10,15}$', phone):
            raise forms.ValidationError("Enter a valid phone number (10-15 digits).")
        return phone


class EmailUpdateForm(forms.Form):
    new_email = forms.EmailField(label='New Email Address')

    def clean_new_email(self):
        email = self.cleaned_data.get('new_email', '').strip()
        if Account.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already in use.")
        return email
